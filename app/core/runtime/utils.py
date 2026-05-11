from typing import List, Tuple, Dict


def rrf_fusion(bm25_results: List[Tuple[int, float]], 
               vector_results: List[Tuple[int, float]], 
               k: int = 60) -> List[Tuple[int, float]]:
    """
    Reciprocal Rank Fusion (RRF) 融合算法
    :param bm25_results: BM25检索结果 [(doc_idx, score), ...]
    :param vector_results: 向量检索结果 [(doc_idx, score), ...]
    :param k: RRF参数，默认60
    :return: 融合后的结果 [(doc_idx, fused_score), ...]
    """
    # 将结果转换为排名字典
    bm25_ranks = {idx: i + 1 for i, (idx, _) in enumerate(bm25_results)}
    vector_ranks = {idx: i + 1 for i, (idx, _) in enumerate(vector_results)}
    
    # 获取所有文档索引
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
    
    # 按分数降序排序
    return sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)


def deduplicate_results(results: List[Tuple[int, float]], 
                        documents: List[Dict], 
                        top_k: int = 3) -> List[str]:
    """
    去重并返回最终回答列表
    :param results: 检索结果 [(doc_idx, score), ...]
    :param documents: 文档列表
    :param top_k: 返回前k个结果
    :return: 去重后的回答列表
    """
    answers = []
    seen = set()
    
    for idx, score in results[:top_k]:
        if idx not in seen and idx < len(documents):
            answers.append(documents[idx]["answer"])
            seen.add(idx)
    
    return answers


def merge_query_results(results_list: List[List[Tuple[int, float]]]) -> List[Tuple[int, float]]:
    """
    合并多个查询变体的检索结果，去重并保留最高分
    :param results_list: 多个查询变体的检索结果列表
    :return: 合并去重后的结果
    """
    merged = {}
    
    for results in results_list:
        for idx, score in results:
            if idx not in merged or score > merged[idx]:
                merged[idx] = score
    
    return sorted(merged.items(), key=lambda x: x[1], reverse=True)