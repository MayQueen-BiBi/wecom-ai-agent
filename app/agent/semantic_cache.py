from typing import Optional, Dict, Any, Tuple
import time
import hashlib
import numpy as np

class SemanticCache:
    """
    语义缓存模块：用于缓存高频重复问题的回答，降低推理成本
    
    功能特性：
    1. 基于语义相似度匹配缓存
    2. 支持缓存过期时间
    3. 提供缓存命中率统计
    4. 支持最大缓存数量限制
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600, similarity_threshold: float = 0.85):
        """
        初始化语义缓存
        :param max_size: 最大缓存条目数
        :param ttl_seconds: 缓存过期时间（秒），默认1小时
        :param similarity_threshold: 语义相似度阈值，超过此值视为命中
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.similarity_threshold = similarity_threshold
        
        # 缓存数据结构
        # {query_hash: {"query": str, "answer": str, "evaluation": dict, "timestamp": float, "embedding": np.ndarray}}
        self.cache = {}
        
        # 统计信息
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_queries": 0
        }
    
    def _compute_embedding(self, text: str) -> np.ndarray:
        """
        计算文本的语义嵌入（基于意图、关键词和字符的组合）
        :param text: 输入文本，格式为 "[意图] 查询内容"
        :return: 语义向量
        """
        # 意图列表（高权重，用于区分不同意图）
        intents = [
            'Symptom_Check', 'Procedure_Explain', 'Process_Flow', 'Price_Inquiry',
            'Comparative_Analysis', 'Risk_Assessment', 'Fear_Relief', 'Price_Objection',
            'Trust_Verification', 'Lead_Generation', 'Logistics_Support', 'Out_of_Scope'
        ]
        
        # 服务类型关键词（高权重）
        service_keywords = [
            '种植牙', '种牙', '缺牙', '牙种植', '人工牙',
            '正畸', '矫正', '牙套', '牙齿矫正', '隐形正畸',
            '洗牙', '洁牙', '牙结石', '牙周清洁', '清洁牙齿',
            '牙周病', '牙周炎', '牙龈炎', '牙周健康', '牙周护理',
            '拔牙', '拔智齿', '牙齿拔除',
            '补牙', '龋齿修复', '牙洞',
            '牙齿松动', '松动', '牙松动', '牙齿不稳',
            '牙龈出血', '刷牙出血', '牙龈红肿'
        ]
        
        # 属性关键词（低权重）
        attribute_keywords = [
            '价格', '费用', '多少钱', '贵吗', '收费',
            '医生', '专家', '医师', '牙医',
            '面诊', '咨询', '检查', '看诊',
            '预约', '挂号', '到院', '看牙', '安排时间',
            '营业时间', '上班时间', '几点开门', '几点关门'
        ]
        
        # 初始化向量：意图(12维) + 服务类型(25维) + 属性(24维) + 字符(50维)
        embedding = np.zeros(12 + 25 + 24 + 50, dtype=np.float32)
        
        # 意图嵌入（最高权重3.0，确保意图不同时相似度降低）
        intent_prefix = text.split(']')[0].strip()[1:] if '[' in text and ']' in text else ''
        for i, intent in enumerate(intents):
            if intent_prefix == intent:
                embedding[i] = 3.0
                break
        
        # 服务类型关键词（高权重2.0）
        for i, keyword in enumerate(service_keywords):
            if keyword in text:
                embedding[12 + i] = 2.0
        
        # 属性关键词（低权重0.5）
        for i, keyword in enumerate(attribute_keywords):
            if keyword in text:
                embedding[12 + 25 + i] = 0.5
        
        # 字符级别嵌入（后50维，权重1.0）
        char_counts = {}
        for char in text:
            if '\u4e00' <= char <= '\u9fff':  # 中文字符
                char_counts[char] = char_counts.get(char, 0) + 1
        
        # 取前50个最常见字符
        sorted_chars = sorted(char_counts.items(), key=lambda x: -x[1])[:50]
        for i, (char, count) in enumerate(sorted_chars):
            embedding[12 + 25 + 24 + i] = count / len(text)
        
        # 归一化
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        计算两个向量的余弦相似度
        :param vec1: 向量1
        :param vec2: 向量2
        :return: 相似度分数（0-1）
        """
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))
    
    def _get_query_hash(self, query: str) -> str:
        """
        计算查询的哈希值
        :param query: 输入查询
        :return: 哈希字符串
        """
        return hashlib.md5(query.encode('utf-8')).hexdigest()
    
    def _clean_expired_entries(self):
        """清理过期的缓存条目"""
        now = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if now - entry["timestamp"] > self.ttl_seconds
        ]
        for key in expired_keys:
            del self.cache[key]
            self.stats["evictions"] += 1
    
    def _evict_oldest_entry(self):
        """移除最旧的缓存条目"""
        if not self.cache:
            return
        
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
        del self.cache[oldest_key]
        self.stats["evictions"] += 1
    
    def get(self, query: str) -> Optional[Tuple[str, Dict]]:
        """
        查询缓存
        :param query: 用户查询
        :return: (answer, evaluation) 如果命中，否则返回None
        """
        self.stats["total_queries"] += 1
        
        # 清理过期条目
        self._clean_expired_entries()
        
        # 计算查询的语义嵌入
        query_embedding = self._compute_embedding(query)
        
        # 查找相似的缓存条目
        best_match = None
        best_similarity = 0.0
        
        for key, entry in self.cache.items():
            similarity = self._cosine_similarity(query_embedding, entry["embedding"])
            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_match = entry
        
        if best_match:
            self.stats["hits"] += 1
            print(f"[SemanticCache] 缓存命中！相似度: {best_similarity:.2f}")
            return (best_match["answer"], best_match["evaluation"])
        
        self.stats["misses"] += 1
        return None
    
    def set(self, query: str, answer: str, evaluation: Dict) -> None:
        """
        设置缓存
        :param query: 用户查询
        :param answer: 回答内容
        :param evaluation: 评估结果
        """
        # 如果缓存已满，先移除最旧的条目
        if len(self.cache) >= self.max_size:
            self._evict_oldest_entry()
        
        # 计算嵌入并存储
        query_hash = self._get_query_hash(query)
        self.cache[query_hash] = {
            "query": query,
            "answer": answer,
            "evaluation": evaluation,
            "timestamp": time.time(),
            "embedding": self._compute_embedding(query)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        :return: 统计字典
        """
        hit_rate = self.stats["hits"] / max(self.stats["total_queries"], 1) * 100
        return {
            **self.stats,
            "hit_rate": f"{hit_rate:.2f}%",
            "current_size": len(self.cache),
            "max_size": self.max_size
        }
    
    def clear(self) -> None:
        """清空所有缓存"""
        self.cache.clear()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_queries": 0
        }


# 全局语义缓存实例
semantic_cache = SemanticCache(
    max_size=1000,
    ttl_seconds=3600,  # 1小时
    similarity_threshold=0.95  # 高阈值：只有非常相似的查询才命中缓存
)


# 测试函数
def test_semantic_cache():
    print("=== 测试语义缓存 ===")
    
    # 测试缓存设置和获取
    semantic_cache.set("种植牙多少钱", "种植牙费用因材料和牙位而异", {"relevance": 0.9, "accuracy": 0.8})
    
    # 测试完全匹配
    result = semantic_cache.get("种植牙多少钱")
    print(f"完全匹配测试 - 命中: {result is not None}")
    
    # 测试语义相似匹配
    result = semantic_cache.get("种植牙价格")
    print(f"语义相似测试 - 命中: {result is not None}")
    
    # 测试不相似查询
    result = semantic_cache.get("洗牙多少钱")
    print(f"不相似测试 - 命中: {result is not None}")
    
    # 打印统计
    stats = semantic_cache.get_stats()
    print(f"统计信息: {stats}")
    
    # 清空缓存
    semantic_cache.clear()
    print("缓存已清空")


if __name__ == "__main__":
    test_semantic_cache()