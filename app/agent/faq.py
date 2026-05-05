from typing import Optional, List, Dict, Tuple
import re
import math
import numpy as np
import faiss

# FAQ知识库
FAQ_KB = [
    {
        "keywords": ["种植牙", "种牙", "缺牙"],
        "answer": "种植牙通常分为检查评估、制定方案、植入与复查几个阶段。费用会因牙位、骨量和材料不同而变化，建议到院拍片后给出准确方案。"
    },
    {
        "keywords": ["正畸", "矫正", "牙套"],
        "answer": "正畸需要先进行口腔检查与面诊评估，再确定是否适合隐形或托槽方案。矫正周期和费用与牙齿基础情况有关。"
    },
    {
        "keywords": ["洗牙", "洁牙", "牙结石"],
        "answer": "洁牙主要用于清除牙结石和牙菌斑，通常建议定期进行。是否需要进一步治疗要以医生检查结果为准。"
    },
    {
        "keywords": ["医生", "专家", "资质"],
        "answer": "我们可安排您到院与对应科室医生面诊，医生资质和擅长方向会在接诊前为您详细介绍。"
    },
    {
        "keywords": ["营业时间", "上班时间", "几点开门"],
        "answer": "门诊常规接诊时间以院方排班为准。您可以告诉我您方便的时段，我先帮您登记预约。"
    },
    {
        "keywords": ["价格", "多少钱", "费用", "贵吗"],
        "answer": "不同项目费用会根据检查结果和治疗方案变化。为了保证准确，我们只提供价格区间参考，最终以医生面诊评估为准。"
    },
]


class BM25Retriever:
    """BM25 检索器"""
    
    def __init__(self, documents: List[Dict], k1: float = 1.5, b: float = 0.75):
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.avg_doc_len = self._calculate_avg_doc_len()
        self.doc_term_freqs = self._precompute_term_freqs()
        self.idf = self._compute_idf()
    
    def _tokenize(self, text: str) -> List[str]:
        """中文分词：字符级 + 关键词提取"""
        # 先去除标点
        text = re.sub(r'[\s!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~。，！？、；：""''（）】【》《]', '', text)
        # 字符级分词（保留中文字符）
        tokens = [char for char in text if '\u4e00' <= char <= '\u9fff']
        return tokens
    
    def _calculate_avg_doc_len(self) -> float:
        total_len = 0
        for doc in self.documents:
            text = " ".join(doc["keywords"]) + " " + doc["answer"]
            tokens = self._tokenize(text)
            total_len += len(tokens)
        return total_len / len(self.documents) if self.documents else 1.0
    
    def _precompute_term_freqs(self) -> List[Dict[str, int]]:
        """预计算每个文档的词频"""
        term_freqs = []
        for doc in self.documents:
            text = " ".join(doc["keywords"]) + " " + doc["answer"]
            tokens = self._tokenize(text)
            freq = {}
            for token in tokens:
                freq[token] = freq.get(token, 0) + 1
            term_freqs.append(freq)
        return term_freqs
    
    def _compute_idf(self) -> Dict[str, float]:
        """计算逆文档频率"""
        idf = {}
        num_docs = len(self.documents)
        
        for doc_idx, doc in enumerate(self.documents):
            text = " ".join(doc["keywords"]) + " " + doc["answer"]
            tokens = set(self._tokenize(text))
            for token in tokens:
                idf[token] = idf.get(token, 0) + 1
        
        for token in idf:
            idf[token] = math.log((num_docs - idf[token] + 0.5) / (idf[token] + 0.5) + 1.0)
        
        return idf
    
    def _score_document(self, query_tokens: List[str], doc_idx: int) -> float:
        """计算单个文档的 BM25 分数"""
        score = 0.0
        doc_len = sum(self.doc_term_freqs[doc_idx].values())
        term_freq = self.doc_term_freqs[doc_idx]
        
        for token in query_tokens:
            if token not in term_freq:
                continue
            
            tf = term_freq[token]
            idf_val = self.idf.get(token, 0.0)
            
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
            score += idf_val * numerator / denominator
        
        return score
    
    def search(self, query: str, top_k: int = 3) -> List[Tuple[int, float]]:
        """执行 BM25 检索"""
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        scores = []
        for idx, _ in enumerate(self.documents):
            score = self._score_document(query_tokens, idx)
            if score > 0:
                scores.append((idx, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class VectorRetriever:
    """向量检索器"""
    
    def __init__(self, documents: List[Dict]):
        self.documents = documents
        self.vector_dim = 256  # 字符级嵌入维度
        self.index = faiss.IndexFlatL2(self.vector_dim)
        self.answers = []
        self._build_index()
    
    def _char_embedding(self, text: str) -> np.ndarray:
        """字符级嵌入：将文本转换为向量"""
        embedding = np.zeros(self.vector_dim, dtype=np.float32)
        chars = [c for c in text if '\u4e00' <= c <= '\u9fff']
        
        if not chars:
            return embedding
        
        for i, char in enumerate(chars[:self.vector_dim]):
            embedding[i] = ord(char) / 65535.0  # 归一化到 [0, 1]
        
        # 添加词频信息
        char_counts = {}
        for char in chars:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        for i, (char, count) in enumerate(char_counts.items()):
            if i < self.vector_dim:
                embedding[i] += count / len(chars)
        
        return embedding
    
    def _build_index(self):
        """构建向量索引"""
        vectors = []
        for doc in self.documents:
            text = " ".join(doc["keywords"]) + " " + doc["answer"]
            vector = self._char_embedding(text)
            vectors.append(vector)
            self.answers.append(doc["answer"])
        
        if vectors:
            vectors_np = np.array(vectors, dtype=np.float32)
            self.index.add(vectors_np)
    
    def search(self, query: str, top_k: int = 3) -> List[Tuple[int, float]]:
        """执行向量检索"""
        query_vector = self._char_embedding(query)
        query_vector_np = np.array([query_vector], dtype=np.float32)
        
        distances, indices = self.index.search(query_vector_np, min(top_k, len(self.documents)))
        
        results = []
        for i, idx in enumerate(indices[0]):
            # 距离越小越相似，转换为分数（距离取反）
            # 对于字符级嵌入，距离范围通常在0-2之间
            score = max(0, 1.0 - distances[0][i] / 2.0)
            if score > 0.05:  # 降低阈值，确保有结果
                results.append((idx, score))
        
        return results


class HybridRetriever:
    """混合检索器：BM25 + 向量检索 + RRF融合"""
    
    def __init__(self, documents: List[Dict]):
        self.bm25 = BM25Retriever(documents)
        self.vector = VectorRetriever(documents)
        self.documents = documents
    
    def _rrf_fusion(self, bm25_results: List[Tuple[int, float]], 
                   vector_results: List[Tuple[int, float]], 
                   k: int = 60) -> List[Tuple[int, float]]:
        """
        RRF (Reciprocal Rank Fusion) 融合
        k: 融合参数，通常取 60-100
        """
        # 创建排名字典
        bm25_ranks = {idx: i + 1 for i, (idx, _) in enumerate(bm25_results)}
        vector_ranks = {idx: i + 1 for i, (idx, _) in enumerate(vector_results)}
        
        # 合并两个结果集
        all_indices = set(bm25_ranks.keys()) | set(vector_ranks.keys())
        
        # 计算融合分数
        fused_scores = {}
        for idx in all_indices:
            bm25_rank = bm25_ranks.get(idx, float('inf'))
            vector_rank = vector_ranks.get(idx, float('inf'))
            
            score = 0.0
            if bm25_rank <= len(bm25_results):
                score += 1.0 / (k + bm25_rank)
            if vector_rank <= len(vector_results):
                score += 1.0 / (k + vector_rank)
            
            fused_scores[idx] = score
        
        # 按分数排序
        sorted_results = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results
    
    def search(self, query: str, top_k: int = 3) -> List[str]:
        """执行混合检索"""
        # 分别执行两种检索
        bm25_results = self.bm25.search(query, top_k=5)
        vector_results = self.vector.search(query, top_k=5)
        
        # RRF 融合
        fused_results = self._rrf_fusion(bm25_results, vector_results)
        
        # 获取答案
        answers = []
        seen = set()
        for idx, score in fused_results[:top_k]:
            if idx not in seen and idx < len(self.documents):
                answers.append(self.documents[idx]["answer"])
                seen.add(idx)
        
        return answers


# 初始化检索器
hybrid_retriever = HybridRetriever(FAQ_KB)


def faq_search(user_text: str) -> Optional[str]:
    """混合检索 FAQ"""
    results = hybrid_retriever.search(user_text, top_k=1)
    if results:
        return results[0]
    return None


# 测试函数
def test_hybrid_search():
    test_queries = [
        "种植牙多少钱",      # 明确关键词
        "牙齿缺失怎么办",     # 语义匹配
        "你们几点开门",      # 明确关键词
        "推荐一个好医生",    # 语义匹配
        "洗牙贵吗",         # 明确关键词
        "正畸周期多长",      # 混合
    ]
    
    print("混合检索测试结果：")
    for query in test_queries:
        result = faq_search(query)
        print(f"Q: {query}")
        print(f"A: {result}")
        print("-" * 50)


if __name__ == "__main__":
    test_hybrid_search()
