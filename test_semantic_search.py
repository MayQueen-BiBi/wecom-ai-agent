#!/usr/bin/env python3
# 测试语义检索效果

from app.core.retrieval.faq import expand_synonyms, faq_search

# 测试同义词扩展
print("=== 同义词扩展测试 ===")
test_texts = [
    "种牙多少钱",
    "牙齿松动怎么办",
    "洗牙贵吗"
]
for text in test_texts:
    expanded = expand_synonyms(text)
    print(f"原始: {text}")
    print(f"扩展: {expanded}")
    print()

# 测试语义检索
print("=== 语义检索测试 ===")
test_queries = [
    "我的牙齿松动了怎么办",
    "牙松动该怎么处理",
    "种植牙多少钱",
    "种牙价格",
    "牙齿缺失怎么办",
    "缺牙有什么解决方案",
    "洗牙贵不贵",
    "洁牙费用多少"
]

for query in test_queries:
    result = faq_search(query)
    print(f"Q: {query}")
    print(f"A: {result}")
    print("-" * 60)

if __name__ == "__main__":
    pass
