# TODO(architecture-freeze): 该模块属于 legacy agent 架构。后续逐步迁移到 workflows/、execution/、core/。
from typing import Optional, List, Dict, Tuple
import requests
import json
from app.config.settings import QWEN_API_KEY
from app.core.cache.cache import semantic_cache
from app.core.retrieval.faq import FAQ_KB, BM25Retriever, VectorRetriever
from app.core.runtime.utils import merge_query_results, rrf_fusion

QWEN_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"


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
            return [(idx, 1.0) for idx, _ in candidates[:top_k]]
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {QWEN_API_KEY}"
        }
        
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
                        results = []
                        for item in scores:
                            doc_id = item.get("doc_id", 0)
                            score = item.get("score", 1) / 5.0
                            if doc_id > 0 and doc_id <= len(candidates):
                                results.append((candidates[doc_id-1][0], score))
                        results.sort(key=lambda x: x[1], reverse=True)
                        return results[:top_k]
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"Rerank error: {e}")
        
        return [(idx, 1.0 - i*0.1) for i, (idx, _) in enumerate(candidates[:top_k])]


class EnhancedHybridRetriever:
    """增强版混合检索器：Query Rewrite + BM25 + 向量检索 + RRF融合 + Rerank"""
    
    def __init__(self, documents: List[Dict]):
        self.documents = documents
        self.bm25 = BM25Retriever(documents)
        self.vector = VectorRetriever(documents)
        self.rewriter = QueryRewriter()
        self.reranker = Reranker()
    
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
                all_bm25_results.append(self.bm25.search(q, top_k=5))
                all_vector_results.append(self.vector.search(q, top_k=5))
        
        # 合并去重并保留最高分
        bm25_results = merge_query_results(all_bm25_results)[:5]
        vector_results = merge_query_results(all_vector_results)[:5]
        
        # Step 3: RRF融合
        fused_results = rrf_fusion(bm25_results, vector_results)
        
        # Step 4: 获取候选文档用于Rerank
        candidates = [(idx, self.documents[idx]["answer"]) for idx, _ in fused_results[:5]]
        
        # Step 5: Rerank精排
        reranked = self.reranker.rerank(query, candidates, top_k=top_k)
        
        # Step 6: 返回最终答案（去重）
        answers = []
        seen = set()
        for idx, score in reranked:
            if idx not in seen and idx < len(self.documents):
                answers.append(self.documents[idx]["answer"])
                seen.add(idx)
        
        return answers

    def search_direct(self, query: str, top_k: int = 3) -> List[str]:
        """
        混合检索（BM25 + 向量 + RRF + Rerank），但跳过 QueryRewrite。
        供 Unified Router 已输出 rewritten_query 时使用，避免重复 LLM、降低延迟。
        """
        q = query.strip()
        if not q:
            return []

        bm25_results = self.bm25.search(q, top_k=5)
        vector_results = self.vector.search(q, top_k=5)
        fused_results = rrf_fusion(bm25_results, vector_results)
        candidates = [
            (idx, self.documents[idx]["answer"])
            for idx, _ in fused_results[:5]
        ]
        reranked = self.reranker.rerank(q, candidates, top_k=top_k)

        answers = []
        seen = set()
        for idx, score in reranked:
            if idx not in seen and idx < len(self.documents):
                answers.append(self.documents[idx]["answer"])
                seen.add(idx)
        return answers


class RAGGenerator:
    """RAG生成器：基于检索结果生成回答，支持multi-hop reasoning和self-check"""
    
    def __init__(self):
        self.qwen_url = QWEN_URL
    
    def _analyze_question_complexity(self, query: str) -> str:
        """分析问题复杂度，判断是否需要多跳推理"""
        if not QWEN_API_KEY:
            return "simple"
        
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
                        你是一个问题分析专家。请判断用户问题的复杂度：
                        - simple: 简单问题，可以直接回答
                        - multi-hop: 需要多跳推理，需要分解为多个子问题
                        - irrelevant: 与牙科知识无关的问题
                        
                        输出格式：只输出 simple、multi-hop 或 irrelevant
                        """
                    },
                    {
                        "role": "user",
                        "content": f"用户问题：{query}"
                    }
                ]
            },
            "parameters": {
                "result_format": "message"
            }
        }
        
        try:
            resp = requests.post(self.qwen_url, headers=headers, json=payload, timeout=3)
            if resp.status_code == 200:
                result = resp.json()
                if "output" in result:
                    return result["output"]["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Question complexity analysis error: {e}")
        
        return "simple"
    
    def _decompose_query(self, query: str) -> List[str]:
        """将复杂问题分解为多个子问题"""
        if not QWEN_API_KEY:
            return [query]
        
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
                        你是一个问题分解专家。请将复杂问题分解为简单的子问题列表，每个子问题应该能够独立回答。
                        输出格式：子问题用 | 分隔，只输出子问题，不要包含其他内容。
                        """
                    },
                    {
                        "role": "user",
                        "content": f"复杂问题：{query}"
                    }
                ]
            },
            "parameters": {
                "result_format": "message"
            }
        }
        
        try:
            resp = requests.post(self.qwen_url, headers=headers, json=payload, timeout=3)
            if resp.status_code == 200:
                result = resp.json()
                if "output" in result:
                    content = result["output"]["choices"][0]["message"]["content"].strip()
                    return [q.strip() for q in content.split("|") if q.strip()]
        except Exception as e:
            print(f"Query decomposition error: {e}")
        
        return [query]
    
    def _synthesize_answers(self, query: str, sub_answers: List[str]) -> str:
        """综合子问题的答案得到最终回答"""
        if not QWEN_API_KEY or len(sub_answers) <= 1:
            return sub_answers[0] if sub_answers else "暂时无法回答您的问题。"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {QWEN_API_KEY}"
        }
        
        answers_text = "\n".join([f"{i+1}. {ans}" for i, ans in enumerate(sub_answers)])
        
        payload = {
            "model": "qwen-flash",
            "input": {
                "messages": [
                    {
                        "role": "system",
                        "content": """
                        你是一个答案综合专家。请将多个子问题的答案综合成一个完整、连贯的回答。
                        规则：
                        1. 保持回答简洁、自然
                        2. 不要提及"子问题"、"综合"等字样
                        3. 如果子答案之间有冲突，以第一个为准
                        """
                    },
                    {
                        "role": "user",
                        "content": f"原始问题：{query}\n子问题答案：\n{answers_text}"
                    }
                ]
            },
            "parameters": {
                "result_format": "message"
            }
        }
        
        try:
            resp = requests.post(self.qwen_url, headers=headers, json=payload, timeout=3)
            if resp.status_code == 200:
                result = resp.json()
                if "output" in result:
                    return result["output"]["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Answer synthesis error: {e}")
        
        return "\n".join(sub_answers)
    
    def _generate_single(self, query: str, context: List[str]) -> str:
        """单跳生成：基于检索到的上下文生成回答"""
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
    
    def generate(self, query: str, context: List[str], enable_multi_hop: bool = True) -> str:
        """
        基于检索到的上下文生成回答，支持多跳推理
        :param query: 用户查询
        :param context: 检索到的上下文文档
        :param enable_multi_hop: 是否启用多跳推理
        :return: 生成的回答
        """
        # 分析问题复杂度
        complexity = self._analyze_question_complexity(query) if enable_multi_hop else "simple"
        
        if complexity == "irrelevant":
            return "这个问题超出了我的知识库范围，我无法回答。"
        
        if complexity == "multi-hop" and enable_multi_hop:
            # 多跳推理：分解问题 -> 逐个回答 -> 综合答案
            sub_queries = self._decompose_query(query)
            sub_answers = []
            
            for sub_q in sub_queries:
                # 对每个子问题进行检索和生成
                sub_answer = self._generate_single(sub_q, context)
                if "无法回答" not in sub_answer:
                    sub_answers.append(sub_answer)
            
            if not sub_answers:
                return "根据我的知识库，无法回答您的问题"
            
            return self._synthesize_answers(query, sub_answers)
        
        # 单跳推理
        return self._generate_single(query, context)


class SelfChecker:
    """Self-check 自我检查模块：检测并降低幻觉风险"""
    
    def __init__(self):
        self.qwen_url = QWEN_URL
    
    def check_factuality(self, query: str, answer: str, context: List[str]) -> Dict[str, float]:
        """
        检查回答的事实正确性
        :param query: 用户查询
        :param answer: 生成的回答
        :param context: 检索到的上下文
        :return: {"factual": 是否符合事实, "confidence": 置信度, "suggestion": 改进建议}
        """
        if not QWEN_API_KEY:
            return {"factual": True, "confidence": 0.5, "suggestion": ""}
        
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
                        你是一个专业的事实检查专家。请检查回答是否基于提供的上下文信息，是否存在幻觉。
                        
                        检查维度：
                        1. 回答中的信息是否都能在上下文中找到依据
                        2. 是否有编造的信息
                        3. 是否有超出上下文范围的断言
                        
                        输出格式：JSON格式 {"factual": true/false, "confidence": 0-10, "suggestion": "改进建议"}
                        - factual: 回答是否符合事实（完全基于上下文）
                        - confidence: 置信度分数（0-10，越高越可信）
                        - suggestion: 如果发现问题，给出改进建议；如果没问题，留空字符串
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
                        result = json.loads(content)
                        return {
                            "factual": result.get("factual", True),
                            "confidence": result.get("confidence", 5) / 10.0,
                            "suggestion": result.get("suggestion", "")
                        }
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"Self-check error: {e}")
        
        return {"factual": True, "confidence": 0.5, "suggestion": ""}
    
    def check_consistency(self, answer: str, previous_answers: List[str] = None) -> bool:
        """
        检查回答与历史回答的一致性
        :param answer: 当前回答
        :param previous_answers: 历史回答列表
        :return: 是否一致
        """
        if not QWEN_API_KEY or not previous_answers:
            return True
        
        history_text = "\n".join([f"{i+1}. {ans}" for i, ans in enumerate(previous_answers)])
        
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
                        你是一个一致性检查专家。请判断新回答是否与历史回答一致。
                        如果存在矛盾或冲突，返回false；否则返回true。
                        输出格式：只输出 true 或 false
                        """
                    },
                    {
                        "role": "user",
                        "content": f"历史回答：\n{history_text}\n\n新回答：{answer}"
                    }
                ]
            },
            "parameters": {
                "result_format": "message"
            }
        }
        
        try:
            resp = requests.post(self.qwen_url, headers=headers, json=payload, timeout=3)
            if resp.status_code == 200:
                result = resp.json()
                if "output" in result:
                    content = result["output"]["choices"][0]["message"]["content"].strip()
                    return content.lower() == "true"
        except Exception as e:
            print(f"Consistency check error: {e}")
        
        return True
    
    def revise_answer(self, query: str, answer: str, context: List[str], suggestion: str) -> str:
        """
        根据建议修正回答
        :param query: 用户查询
        :param answer: 原始回答
        :param context: 检索到的上下文
        :param suggestion: 改进建议
        :return: 修正后的回答
        """
        if not QWEN_API_KEY or not suggestion:
            return answer
        
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
                        你是一个回答修正专家。请根据建议和上下文修正回答，确保完全基于上下文信息。
                        ⚠️ 严格规则：
                        1. 必须基于提供的上下文信息回答问题
                        2. 如果上下文没有相关信息，直接说"根据我的知识库，无法回答您的问题"
                        3. 禁止编造信息，禁止产生幻觉
                        """
                    },
                    {
                        "role": "user",
                        "content": f"用户问题：{query}\n参考上下文：\n{context_text}\n\n原始回答：{answer}\n\n改进建议：{suggestion}\n\n请给出修正后的回答："
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
            print(f"Answer revision error: {e}")
        
        return answer


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
enhanced_retriever = EnhancedHybridRetriever(FAQ_KB)
rag_generator = RAGGenerator()
self_checker = SelfChecker()
llm_evaluator = LLMEvaluator()


def rag_search(user_text: str, use_rerank: bool = True, use_generator: bool = True, 
               enable_multi_hop: bool = True, enable_self_check: bool = True, 
               use_cache: bool = True) -> Tuple[Optional[str], Dict]:
    """
    增强版RAG检索：支持multi-hop reasoning、self-check和语义缓存
    :param user_text: 用户输入
    :param use_rerank: 是否使用rerank
    :param use_generator: 是否使用生成器
    :param enable_multi_hop: 是否启用多跳推理
    :param enable_self_check: 是否启用自我检查
    :param use_cache: 是否使用语义缓存
    :return: (回答, 评估结果)
    """
    # 步骤1：查询语义缓存（如果启用）
    if use_cache:
        cached_result = semantic_cache.get(user_text)
        if cached_result:
            answer, evaluation = cached_result
            evaluation["cache_hit"] = True
            return answer, evaluation
    
    # 步骤2：执行正常RAG检索流程
    contexts = enhanced_retriever.search(user_text, top_k=3)
    
    if not contexts:
        return None, {"relevance": 0, "accuracy": 0, "usefulness": 0, "self_check": {"factual": True, "confidence": 0.0}, "cache_hit": False}
    
    if use_generator:
        answer = rag_generator.generate(user_text, contexts, enable_multi_hop=enable_multi_hop)
    else:
        answer = contexts[0]
    
    # Self-check 自我检查
    self_check_result = {"factual": True, "confidence": 1.0, "suggestion": ""}
    if enable_self_check:
        self_check_result = self_checker.check_factuality(user_text, answer, contexts)
        
        # 如果检测到幻觉，尝试修正
        if not self_check_result["factual"] or self_check_result["confidence"] < 0.5:
            if self_check_result["suggestion"]:
                answer = self_checker.revise_answer(user_text, answer, contexts, self_check_result["suggestion"])
            else:
                # 置信度太低，返回兜底回答
                answer = "根据我的知识库，无法准确回答您的问题。建议您到院咨询专业医生。"
    
    # LLM评估
    evaluation = llm_evaluator.evaluate(user_text, answer, contexts)
    evaluation["self_check"] = self_check_result
    evaluation["cache_hit"] = False
    
    # 步骤3：将结果存入语义缓存（如果启用）
    if use_cache and answer:
        semantic_cache.set(user_text, answer, evaluation)
    
    return answer, evaluation


def get_cache_stats() -> Dict[str, any]:
    """
    获取语义缓存统计信息
    :return: 统计字典
    """
    return semantic_cache.get_stats()


def clear_cache() -> None:
    """清空语义缓存"""
    semantic_cache.clear()
    print("[SemanticCache] 缓存已清空")


# 测试函数
def test_enhanced_rag():
    test_queries = [
        "种植牙多少钱",
        "牙齿缺失怎么办",
        "你们几点开门",
        "推荐一个好医生",
        "洗牙贵吗",
        "正畸周期多长",
        "牙齿松动了怎么办",
        "种植牙和正畸哪个更贵",  # 复杂问题，需要多跳推理
        "洗牙需要预约吗，费用多少",  # 多意图问题
    ]
    
    print("增强版RAG测试结果（含multi-hop和self-check）：")
    for query in test_queries:
        answer, evaluation = rag_search(query, enable_multi_hop=True, enable_self_check=True)
        print(f"Q: {query}")
        print(f"A: {answer}")
        print(f"评估：相关性={evaluation['relevance']:.2f}, 准确性={evaluation['accuracy']:.2f}, 有用性={evaluation['usefulness']:.2f}")
        if 'self_check' in evaluation:
            sc = evaluation['self_check']
            print(f"自检：符合事实={sc.get('factual', 'N/A')}, 置信度={sc.get('confidence', 0.0):.2f}")
        print("-" * 60)


if __name__ == "__main__":
    test_enhanced_rag()