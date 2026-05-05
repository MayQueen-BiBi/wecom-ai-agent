from typing import Optional, List, Dict, Tuple
import re
import math
import numpy as np
import faiss
import requests
from app.config.settings import QWEN_API_KEY

QWEN_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

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
        """中文分词：字符级"""
        text = re.sub(r'[\s!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~。，！？、；：""''（）】【》《]', '', text)
        return [char for char in text if '\u4e00' <= char <= '\u9fff']
    
    def _calculate_avg_doc_len(self) -> float:
        total_len = 0
        for doc in self.documents:
            text = " ".join(doc["keywords"]) + " " + doc["answer"]
            total_len += len(self._tokenize(text))
        return total_len / len(self.documents) if self.documents else 1.0
    
    def _precompute_term_freqs(self) -> List[Dict[str, int]]:
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
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
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
        self.vector_dim = 256
        self.index = faiss.IndexFlatL2(self.vector_dim)
        self.answers = []
        self._build_index()
    
    def _char_embedding(self, text: str) -> np.ndarray:
        embedding = np.zeros(self.vector_dim, dtype=np.float32)
        chars = [c for c in text if '\u4e00' <= c <= '\u9fff']
        if not chars:
            return embedding
        for i, char in enumerate(chars[:self.vector_dim]):
            embedding[i] = ord(char) / 65535.0
        char_counts = {}
        for char in chars:
            char_counts[char] = char_counts.get(char, 0) + 1
        for i, (char, count) in enumerate(char_counts.items()):
            if i < self.vector_dim:
                embedding[i] += count / len(chars)
        return embedding
    
    def _build_index(self):
        vectors = []
        for doc in self.documents:
            text = " ".join(doc["keywords"]) + " " + doc["answer"]
            vector = self._char_embedding(text)
            vectors.append(vector)
            self.answers.append(doc["answer"])
        if vectors:
            self.index.add(np.array(vectors, dtype=np.float32))
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        query_vector = self._char_embedding(query)
        distances, indices = self.index.search(np.array([query_vector], dtype=np.float32), min(top_k, len(self.documents)))
        results = []
        for i, idx in enumerate(indices[0]):
            score = max(0, 1.0 - distances[0][i] / 2.0)
            if score > 0.05:
                results.append((idx, score))
        return results


class QueryRewriter:
    """Query Rewrite 模块：让LLM参与理解用户问题"""
    
    def __init__(self):
        self.qwen_url = QWEN_URL
    
    def rewrite(self, query: str) -> str:
        """重写用户查询，增强检索效果"""
        if not QWEN_API_KEY:
            return query
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {QWEN_API_KEY}"
        }
        
        payload = {
            "model": "qwen-flash",
            "input": {
                "messages": [
                    {
                        "role": "system",
                        "content": """
                        你是一个专业的问题改写助手。请将用户的问题进行改写，使其更适合FAQ检索。
                        规则：
                        1. 识别问题的核心意图和关键词
                        2. 生成1-3个改写版本，用"|"分隔
                        3. 保留原问题的核心含义
                        4. 不要添加无关信息
                        5. 如果原问题已经很清晰，可以返回原问题
                        输出格式：只输出改写后的问题，不要包含其他内容
                        """
                    },
                    {
                        "role": "user",
                        "content": f"原始问题：{query}"
                    }
                ]
            },
            "parameters": {
                "result_format": "message"
            }
        }
        
        try:
            resp = requests.post(self.qwen_url, headers=headers, json=payload, timeout=5)
            if resp.status_code == 200:
                result = resp.json()
                if "output" in result:
                    rewritten = result["output"]["choices"][0]["message"]["content"].strip()
                    return rewritten
        except Exception as e:
            print(f"Query Rewrite error: {e}")
        
        return query


class Reranker:
    """Rerank 模块：对候选文档进行精排"""
    
    def __init__(self):
        self.qwen_url = QWEN_URL
    
    def rerank(self, query: str, candidates: List[Tuple[int, str]], top_k: int = 3) -> List[Tuple[int, float]]:
        """
        对候选文档进行重排序
        :param query: 用户查询
        :param candidates: 候选文档列表 [(doc_idx, answer), ...]
        :param top_k: 返回前k个结果
        :return: 重排序后的结果 [(doc_idx, score), ...]
        """
        if not QWEN_API_KEY or len(candidates) <= top_k:
            # 没有LLM时，返回原始顺序（分数为1.0）
            return [(idx, 1.0) for idx, _ in candidates[:top_k]]
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {QWEN_API_KEY}"
        }
        
        # 构建候选文档列表
        docs_text = "\n".join([f"{i+1}. {doc[1]}" for i, doc in enumerate(candidates)])
        
        payload = {
            "model": "qwen-flash",
            "input": {
                "messages": [
                    {
                        "role": "system",
                        "content": """
                        你是一个专业的文档排序助手。请根据与用户问题的相关性，对提供的候选文档进行评分。
                        评分规则：
                        1. 相关性最高的文档评分为5分
                        2. 相关性最低的文档评分为1分
                        3. 请给出每个文档的分数，用JSON格式输出
                        输出格式：[{"doc_id": 文档编号, "score": 分数}, ...]
                        """
                    },
                    {
                        "role": "user",
                        "content": f"用户问题：{query}\n候选文档：\n{docs_text}"
                    }
                ]
            },
            "parameters": {
                "result_format": "message"
            }
        }
        
        try:
            resp = requests.post(self.qwen_url, headers=headers, json=payload, timeout=5)
            if resp.status_code == 200:
                result = resp.json()
                if "output" in result:
                    content = result["output"]["choices"][0]["message"]["content"].strip()
                    try:
                        scores = json.loads(content)
                        # 转换为(doc_idx, score)格式
                        results = []
                        for item in scores:
                            doc_id = item.get("doc_id", 0)
                            score = item.get("score", 1) / 5.0  # 归一化到[0,1]
                            if doc_id > 0 and doc_id <= len(candidates):
                                results.append((candidates[doc_id-1][0], score))
                        # 按分数排序
                        results.sort(key=lambda x: x[1], reverse=True)
                        return results[:top_k]
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"Rerank error: {e}")
        
        # 降级处理：返回原始候选
        return [(idx, 1.0 - i*0.1) for i, (idx, _) in enumerate(candidates[:top_k])]


class HybridRetriever:
    """混合检索器：Query Rewrite + BM25 + 向量检索 + RRF融合 + Rerank"""
    
    def __init__(self, documents: List[Dict]):
        self.documents = documents
        self.bm25 = BM25Retriever(documents)
        self.vector = VectorRetriever(documents)
        self.rewriter = QueryRewriter()
        self.reranker = Reranker()
    
    def _rrf_fusion(self, bm25_results: List[Tuple[int, float]], 
                   vector_results: List[Tuple[int, float]], 
                   k: int = 60) -> List[Tuple[int, float]]:
        bm25_ranks = {idx: i + 1 for i, (idx, _) in enumerate(bm25_results)}
        vector_ranks = {idx: i + 1 for i, (idx, _) in enumerate(vector_results)}
        all_indices = set(bm25_ranks.keys()) | set(vector_ranks.keys())
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
        return sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    
    def search(self, query: str, top_k: int = 3) -> List[str]:
        """执行增强版混合检索"""
        # Step 1: Query Rewrite
        rewritten_queries = self.rewriter.rewrite(query)
        query_variants = rewritten_queries.split("|")
        
        # Step 2: 对每个改写版本执行检索
        all_bm25_results = []
        all_vector_results = []
        
        for q in query_variants:
            q = q.strip()
            if q:
                all_bm25_results.extend(self.bm25.search(q, top_k=5))
                all_vector_results.extend(self.vector.search(q, top_k=5))
        
        # 去重并保留最高分
        bm25_unique = {}
        for idx, score in all_bm25_results:
            if idx not in bm25_unique or score > bm25_unique[idx]:
                bm25_unique[idx] = score
        bm25_results = sorted(bm25_unique.items(), key=lambda x: x[1], reverse=True)[:5]
        
        vector_unique = {}
        for idx, score in all_vector_results:
            if idx not in vector_unique or score > vector_unique[idx]:
                vector_unique[idx] = score
        vector_results = sorted(vector_unique.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Step 3: RRF融合
        fused_results = self._rrf_fusion(bm25_results, vector_results)
        
        # Step 4: 获取候选文档用于Rerank
        candidates = [(idx, self.documents[idx]["answer"]) for idx, _ in fused_results[:5]]
        
        # Step 5: Rerank精排
        reranked = self.reranker.rerank(query, candidates, top_k=top_k)
        
        # Step 6: 返回最终答案
        answers = []
        seen = set()
        for idx, score in reranked:
            if idx not in seen and idx < len(self.documents):
                answers.append(self.documents[idx]["answer"])
                seen.add(idx)
        
        return answers


class RAGGenerator:
    """RAG生成器：基于检索结果生成回答，通过prompt约束减少幻觉"""
    
    def __init__(self):
        self.qwen_url = QWEN_URL
    
    def generate(self, query: str, context: List[str]) -> str:
        """
        基于检索到的上下文生成回答
        :param query: 用户查询
        :param context: 检索到的上下文文档
        :return: 生成的回答
        """
        if not QWEN_API_KEY:
            return context[0] if context else "暂时无法回答您的问题。"
        
        context_text = "\n".join([f"{i+1}. {doc}" for i, doc in enumerate(context)])
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {QWEN_API_KEY}"
        }
        
        payload = {
            "model": "qwen-flash",
            "input": {
                "messages": [
                    {
                        "role": "system",
                        "content": """
                        你是一个专业的牙科医院客服助理。
                        
                        ⚠️ 严格规则：
                        1. 必须基于提供的上下文信息回答问题
                        2. 如果上下文没有相关信息，直接说"根据我的知识库，无法回答您的问题"
                        3. 禁止编造信息，禁止产生幻觉
                        4. 回答要简洁、准确，用自然友好的语言
                        5. 不要提及"根据文档"、"根据上下文"等字样
                        6. 禁止做出诊断和疗效承诺
                        7. 如果用户问的是预约相关问题，引导他们提供姓名和电话
                        """
                    },
                    {
                        "role": "user",
                        "content": f"上下文信息：\n{context_text}\n\n用户问题：{query}"
                    }
                ]
            },
            "parameters": {
                "result_format": "message"
            }
        }
        
        try:
            resp = requests.post(self.qwen_url, headers=headers, json=payload, timeout=5)
            if resp.status_code == 200:
                result = resp.json()
                if "output" in result:
                    return result["output"]["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"RAG Generation error: {e}")
        
        return context[0] if context else "暂时无法回答您的问题。"


class LLMEvaluator:
    """LLM-as-a-judge 评估体系"""
    
    def __init__(self):
        self.qwen_url = QWEN_URL
    
    def evaluate(self, query: str, answer: str, context: List[str]) -> Dict[str, float]:
        """
        评估回答质量
        :param query: 用户查询
        :param answer: 生成的回答
        :param context: 检索到的上下文
        :return: 评估结果字典
        """
        if not QWEN_API_KEY:
            return {"relevance": 0.5, "accuracy": 0.5, "usefulness": 0.5}
        
        context_text = "\n".join([f"{i+1}. {doc}" for i, doc in enumerate(context)])
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {QWEN_API_KEY}"
        }
        
        payload = {
            "model": "qwen-flash",
            "input": {
                "messages": [
                    {
                        "role": "system",
                        "content": """
                        你是一个专业的AI回答评估专家。请从以下三个维度评估回答质量：
                        
                        1. 相关性(Relevance)：回答与用户问题的相关程度
                        2. 准确性(Accuracy)：回答内容的正确性，是否基于提供的上下文
                        3. 有用性(Usefulness)：回答对用户是否有帮助
                        
                        每个维度评分范围：0-10分
                        输出格式：JSON格式 {"relevance": 分数, "accuracy": 分数, "usefulness": 分数}
                        """
                    },
                    {
                        "role": "user",
                        "content": f"用户问题：{query}\n参考上下文：\n{context_text}\n\n回答：{answer}"
                    }
                ]
            },
            "parameters": {
                "result_format": "message"
            }
        }
        
        try:
            resp = requests.post(self.qwen_url, headers=headers, json=payload, timeout=5)
            if resp.status_code == 200:
                result = resp.json()
                if "output" in result:
                    content = result["output"]["choices"][0]["message"]["content"].strip()
                    try:
                        scores = json.loads(content)
                        # 归一化到[0,1]
                        return {
                            "relevance": scores.get("relevance", 5) / 10.0,
                            "accuracy": scores.get("accuracy", 5) / 10.0,
                            "usefulness": scores.get("usefulness", 5) / 10.0
                        }
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"LLM Evaluator error: {e}")
        
        return {"relevance": 0.5, "accuracy": 0.5, "usefulness": 0.5}


# 初始化增强版RAG组件
hybrid_retriever = HybridRetriever(FAQ_KB)
rag_generator = RAGGenerator()
llm_evaluator = LLMEvaluator()


def rag_search(user_text: str, use_rerank: bool = True, use_generator: bool = True) -> Tuple[Optional[str], Dict]:
    """
    增强版RAG检索
    :param user_text: 用户输入
    :param use_rerank: 是否使用rerank
    :param use_generator: 是否使用生成器
    :return: (回答, 评估结果)
    """
    # 执行检索
    contexts = hybrid_retriever.search(user_text, top_k=3)
    
    if not contexts:
        return None, {"relevance": 0, "accuracy": 0, "usefulness": 0}
    
    # 生成回答
    if use_generator:
        answer = rag_generator.generate(user_text, contexts)
    else:
        answer = contexts[0]
    
    # 评估回答质量
    evaluation = llm_evaluator.evaluate(user_text, answer, contexts)
    
    return answer, evaluation


# 测试函数
def test_enhanced_rag():
    test_queries = [
        "种植牙多少钱",
        "牙齿缺失怎么办",
        "你们几点开门",
        "推荐一个好医生",
        "洗牙贵吗",
        "正畸周期多长",
    ]
    
    print("增强版RAG测试结果：")
    for query in test_queries:
        answer, evaluation = rag_search(query)
        print(f"Q: {query}")
        print(f"A: {answer}")
        print(f"评估：相关性={evaluation['relevance']:.2f}, 准确性={evaluation['accuracy']:.2f}, 有用性={evaluation['usefulness']:.2f}")
        print("-" * 60)


if __name__ == "__main__":
    import json
    test_enhanced_rag()