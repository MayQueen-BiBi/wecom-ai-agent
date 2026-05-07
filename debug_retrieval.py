#!/usr/bin/env python3
# 诊断检索问题

from app.agent.faq import FAQ_KB, BM25Retriever, VectorRetriever, HybridRetriever

query = "我的牙齿松动了怎么办"
print(f"分析查询: {query}")
print()

# 测试BM25检索
bm25 = BM25Retriever(FAQ_KB)
bm25_results = bm25.search(query, top_k=5)
print("=== BM25检索结果 ===")
for idx, score in bm25_results:
    print(f"分数: {score:.4f} - {FAQ_KB[idx]['keywords'][:3]}")

print()

# 测试向量检索
vector = VectorRetriever(FAQ_KB)
vector_results = vector.search(query, top_k=5)
print("=== 向量检索结果 ===")
for idx, score in vector_results:
    print(f"分数: {score:.4f} - {FAQ_KB[idx]['keywords'][:3]}")

print()

# 测试混合检索
hybrid = HybridRetriever(FAQ_KB)
hybrid_results = hybrid.search(query, top_k=5)
print("=== 混合检索结果 ===")
for i, ans in enumerate(hybrid_results):
    print(f"{i+1}. {ans}")
