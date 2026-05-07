from typing import Optional, List, Dict, Tuple
import re
import math
import numpy as np
import faiss

from app.agent.utils import rrf_fusion, deduplicate_results

# 牙科领域同义词词典 - 用于提升语义理解
SYNONYM_DICT = {
    "种植牙": ["种植牙", "种牙", "人工牙", "牙种植"],
    "正畸": ["正畸", "矫正", "牙套", "牙齿矫正"],
    "洗牙": ["洗牙", "洁牙", "牙结石清理", "清洁牙齿"],
    "医生": ["医生", "专家", "医师", "牙医"],
    "价格": ["价格", "费用", "多少钱", "贵吗", "收费"],
    "面诊": ["面诊", "咨询", "检查", "看诊"],
    "营业时间": ["营业时间", "上班时间", "几点开门", "几点关门"],
    "牙齿松动": ["牙齿松动", "松动", "牙松动", "牙齿不稳"],
    "拔牙": ["拔牙", "拔智齿", "牙齿拔除"],
    "补牙": ["补牙", "龋齿修复", "牙洞"],
}

def expand_synonyms(text: str) -> str:
    """
    同义词扩展：将文本中的关键词替换为其同义词列表
    双向匹配：不仅匹配keyword，也匹配synonyms中的词
    例如："种牙多少钱" → "种牙 种植牙 人工牙 牙种植 多少钱 价格 费用"
    """
    expanded = text
    for keyword, synonyms in SYNONYM_DICT.items():
        # 双向匹配：keyword或任何同义词出现在文本中都触发扩展
        all_terms = [keyword] + synonyms
        if any(term in text for term in all_terms):
            expanded += " " + " ".join(synonyms)
    return expanded

# FAQ知识库（带metadata）
# layer: MEDICAL_KNOWLEDGE | USER_DECISION | OBJECTION_HANDLING | BUSINESS_CONVERSION
# category: 科室分类
FAQ_KB = [
    {
        "keywords": ["种植牙", "种牙", "缺牙", "牙种植", "人工牙"],
        "answer": "种植牙通常分为检查评估、制定方案、植入与复查几个阶段。费用会因牙位、骨量和材料不同而变化，建议到院拍片后给出准确方案。",
        "layer": "MEDICAL_KNOWLEDGE",
        "category": "种植科"
    },
    {
        "keywords": ["种植牙疼吗", "种牙疼吗", "种植牙疼痛", "种牙疼痛"],
        "answer": "种植牙手术过程中会进行局部麻醉，您基本不会感到疼痛。术后可能会有轻微肿胀和不适感，医生会开具止痛药和消炎药，通常一周左右即可恢复。我们采用先进的无痛技术，让您的治疗过程更加舒适。",
        "layer": "OBJECTION_HANDLING",
        "category": "种植科"
    },
    {
        "keywords": ["正畸", "矫正", "牙套", "牙齿矫正", "隐形正畸"],
        "answer": "正畸需要先进行口腔检查与面诊评估，再确定是否适合隐形或托槽方案。矫正周期和费用与牙齿基础情况有关。",
        "layer": "MEDICAL_KNOWLEDGE",
        "category": "正畸科"
    },
    {
        "keywords": ["洗牙", "洁牙", "牙结石", "牙周清洁"],
        "answer": "洁牙主要用于清除牙结石和牙菌斑，通常建议定期进行。是否需要进一步治疗要以医生检查结果为准。",
        "layer": "MEDICAL_KNOWLEDGE",
        "category": "牙周科"
    },
    {
        "keywords": ["牙周病", "牙周炎", "牙龈炎", "牙周健康"],
        "answer": "牙周病是指发生在牙齿周围支持组织的疾病，包括牙龈炎和牙周炎。早期症状可能包括牙龈红肿、出血、口臭等，建议定期口腔检查。",
        "layer": "MEDICAL_KNOWLEDGE",
        "category": "牙周科"
    },
    {
        "keywords": ["牙齿松动", "松动", "牙松动", "牙齿不稳"],
        "answer": "牙齿松动可能由多种原因引起，建议尽快到院检查。医生会根据松动程度给出专业建议，可能需要进行固定或其他治疗。",
        "layer": "MEDICAL_KNOWLEDGE",
        "category": "牙周科"
    },
    {
        "keywords": ["根管治疗", "根管"],
        "answer": "根管治疗是治疗牙髓病和根尖周病的有效方法，通过清除根管内的感染物质并严密充填，保留患牙。具体需医生检查后确定。",
        "layer": "MEDICAL_KNOWLEDGE",
        "category": "牙体牙髓科"
    },
    {
        "keywords": ["拔牙", "拔智齿", "牙齿拔除"],
        "answer": "拔牙是口腔科常见的小手术，术前会进行局部麻醉。智齿拔除后需遵循医嘱进行术后护理，一般一周左右可恢复。",
        "layer": "MEDICAL_KNOWLEDGE",
        "category": "口腔外科"
    },
    {
        "keywords": ["补牙", "龋齿修复", "牙洞"],
        "answer": "补牙是用树脂等材料修复牙齿缺损的方法，通常一次就诊即可完成。建议发现蛀牙及时治疗，避免损伤牙神经。",
        "layer": "MEDICAL_KNOWLEDGE",
        "category": "牙体牙髓科"
    },
    {
        "keywords": ["牙龈出血", "刷牙出血", "牙龈红肿"],
        "answer": "牙龈出血通常是牙龈炎的信号，建议及时到院检查。医生会根据情况进行专业清洁和指导。",
        "layer": "MEDICAL_KNOWLEDGE",
        "category": "牙周科"
    },
    {
        "keywords": ["价格", "多少钱", "费用", "贵吗", "收费"],
        "answer": "不同项目费用会根据检查结果和治疗方案变化。为了保证准确，我们只提供价格区间参考，最终以医生面诊评估为准。",
        "layer": "USER_DECISION",
        "category": "综合"
    },
    {
        "keywords": ["国产", "进口", "对比", "哪个好", "选哪个"],
        "answer": "国产和进口材料各有优势。国产材料性价比高，进口材料在某些性能上更优。具体选择需结合您的口腔状况和预算，建议到院咨询。",
        "layer": "USER_DECISION",
        "category": "综合"
    },
    {
        "keywords": ["风险", "后遗症", "成功率", "会掉吗", "安全吗"],
        "answer": "牙科治疗技术已经非常成熟，成功率很高。任何治疗都有一定风险，医生会在术前详细说明。遵循术后护理指导可有效降低风险。",
        "layer": "USER_DECISION",
        "category": "综合"
    },
    {
        "keywords": ["怕疼", "疼痛", "麻醉", "无痛"],
        "answer": "我们采用先进的无痛麻醉技术，治疗过程中基本不会感到疼痛。医生会全程关注您的感受，确保舒适体验。",
        "layer": "OBJECTION_HANDLING",
        "category": "综合"
    },
    {
        "keywords": ["太贵", "便宜点", "优惠", "打折"],
        "answer": "我们的定价基于使用的材料品质和医生的专业技术。虽然价格不是最低的，但我们提供优质的服务和可靠的治疗效果，性价比很高。",
        "layer": "OBJECTION_HANDLING",
        "category": "综合"
    },
    {
        "keywords": ["医生", "专家", "资质", "案例", "荣誉"],
        "answer": "我们的医生均来自知名口腔院校，拥有丰富的临床经验。您可以查看医生的详细介绍和成功案例，我们也会为您安排适合的专家。",
        "layer": "OBJECTION_HANDLING",
        "category": "综合"
    },
    {
        "keywords": ["预约", "挂号", "看牙", "安排时间"],
        "answer": "好的，我来帮您预约。请先告诉我您的称呼（姓名）。",
        "layer": "BUSINESS_CONVERSION",
        "category": "综合"
    },
    {
        "keywords": ["地址", "位置", "停车", "营业时间", "医保"],
        "answer": "我们位于市中心，交通便利，设有免费停车场。门诊时间为周一至周日，支持医保卡结算。具体地址和联系方式会在预约成功后发送给您。",
        "layer": "BUSINESS_CONVERSION",
        "category": "综合"
    },
    {
        "keywords": ["复诊", "复查", "几次", "周期", "时间"],
        "answer": "不同治疗的复诊次数不同。种植牙通常需要3-4次复诊，正畸则需要每月复诊一次。具体时间安排会由医生在治疗开始时告知您。",
        "layer": "MEDICAL_KNOWLEDGE",
        "category": "综合"
    },
    {
        "keywords": ["牙齿缺失", "缺牙", "牙齿掉了"],
        "answer": "牙齿缺失可以通过种植牙、活动义齿或固定桥等方式修复。建议到院进行口腔检查，医生会根据您的口腔状况和需求给出最合适的方案。",
        "layer": "MEDICAL_KNOWLEDGE",
        "category": "种植科"
    },
    {
        "keywords": ["推荐医生", "好医生", "专家", "选择医生"],
        "answer": "我们拥有一支经验丰富的医疗团队，每位医生都有各自的专业领域。您可以根据您的需求选择对应科室的医生，我们也可以根据您的情况为您推荐合适的专家。",
        "layer": "OBJECTION_HANDLING",
        "category": "综合"
    },
    {
        "keywords": ["几点开门", "几点关门", "营业时间", "门诊时间"],
        "answer": "我们的门诊时间为周一至周日 9:00-18:00，节假日正常营业。建议提前预约，避免长时间等待。",
        "layer": "BUSINESS_CONVERSION",
        "category": "综合"
    },
    {
        "keywords": ["牙龈出血", "刷牙出血", "牙龈红肿"],
        "answer": "牙龈出血通常是牙龈炎的信号，可能与牙结石堆积、刷牙方式不当等有关。建议及时到院进行专业清洁，医生会根据情况给出治疗建议。",
        "layer": "MEDICAL_KNOWLEDGE",
        "category": "牙周科"
    },
    {
        "keywords": ["地址", "位置", "在哪里", "医院地址", "诊所地址"],
        "answer": "我们位于市中心繁华地段，交通便利。具体地址会在您预约成功后通过短信发送给您，也可以在我们的官方网站上查看详细地图。",
        "layer": "GENERAL_SUPPORT",
        "category": "综合"
    },
    {
        "keywords": ["停车", "停车场", "车位", "停车方便吗"],
        "answer": "我们提供免费地下停车场，就诊患者可享受3小时免费停车。停车场入口位于医院北侧，有专人引导。",
        "layer": "GENERAL_SUPPORT",
        "category": "综合"
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
    
    def search(self, query: str, top_k: int = 5, filter_dict: Optional[Dict[str, str]] = None) -> List[Tuple[int, float]]:
        """
        执行BM25检索，支持metadata过滤
        :param query: 用户查询
        :param top_k: 返回前k个结果
        :param filter_dict: 过滤条件，如 {"layer": "MEDICAL_KNOWLEDGE", "category": "种植科"}
        :return: [(文档索引, 分数), ...]
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        # 过滤文档
        filtered_indices = []
        for idx, doc in enumerate(self.documents):
            if filter_dict:
                match = True
                for key, value in filter_dict.items():
                    if doc.get(key) != value:
                        match = False
                        break
                if match:
                    filtered_indices.append(idx)
            else:
                filtered_indices.append(idx)
        
        scores = []
        for idx in filtered_indices:
            score = self._score_document(query_tokens, idx)
            if score > 0:
                scores.append((idx, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class VectorRetriever:
    """语义向量检索器：基于关键词匹配的语义嵌入"""
    
    def __init__(self, documents: List[Dict]):
        self.documents = documents
        self.vector_dim = len(documents) * 2  # 每个文档分配2个维度
        self.index = faiss.IndexFlatL2(self.vector_dim)
        self.answers = []
        self._build_index()
    
    def _semantic_embedding(self, text: str) -> np.ndarray:
        """
        语义嵌入：基于关键词匹配的稀疏向量
        每个文档对应一个维度，匹配到关键词则该维度为权重值
        """
        # 同义词扩展
        expanded_text = expand_synonyms(text)
        
        embedding = np.zeros(self.vector_dim, dtype=np.float32)
        
        # 为每个文档计算匹配分数
        for doc_idx, doc in enumerate(self.documents):
            match_score = 0.0
            matched_count = 0
            
            for kw in doc["keywords"]:
                if kw in expanded_text:
                    # 匹配到关键词，增加分数
                    match_score += 1.0
                    matched_count += 1
            
            # 如果匹配到关键词，设置对应维度
            if matched_count > 0:
                # 匹配分数 = 匹配的关键词数 / 总关键词数
                embedding[doc_idx] = match_score / len(doc["keywords"])
                # 第二个维度存储匹配的关键词数量
                embedding[doc_idx + len(self.documents)] = matched_count
        
        # 归一化
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def _build_index(self):
        """构建语义向量索引"""
        vectors = []
        for doc in self.documents:
            text = " ".join(doc["keywords"]) + " " + doc["answer"]
            vector = self._semantic_embedding(text)
            vectors.append(vector)
            self.answers.append(doc["answer"])
        if vectors:
            self.index.add(np.array(vectors, dtype=np.float32))
    
    def search(self, query: str, top_k: int = 5, filter_dict: Optional[Dict[str, str]] = None) -> List[Tuple[int, float]]:
        """
        执行语义检索，支持metadata过滤
        :param query: 用户查询
        :param top_k: 返回前k个结果
        :param filter_dict: 过滤条件，如 {"layer": "MEDICAL_KNOWLEDGE"}
        :return: [(文档索引, 相似度分数), ...]
        """
        query_vector = self._semantic_embedding(query)
        distances, indices = self.index.search(
            np.array([query_vector], dtype=np.float32), 
            min(top_k * 2, len(self.documents))  # 先获取更多结果用于过滤
        )
        
        results = []
        for i, idx in enumerate(indices[0]):
            # 应用过滤条件
            if filter_dict:
                doc = self.documents[idx]
                match = True
                for key, value in filter_dict.items():
                    if doc.get(key) != value:
                        match = False
                        break
                if not match:
                    continue
            
            # 将L2距离转换为相似度分数（距离越小相似度越高）
            max_distance = 1.5
            score = max(0, 1.0 - distances[0][i] / max_distance)
            if score > 0.05:
                results.append((idx, score))
        
        return results[:top_k]


class HybridRetriever:
    """混合检索器：BM25 + 向量检索 + RRF融合"""
    
    def __init__(self, documents: List[Dict]):
        self.documents = documents
        self.bm25 = BM25Retriever(documents)
        self.vector = VectorRetriever(documents)
    
    def search(self, query: str, top_k: int = 3, filter_dict: Optional[Dict[str, str]] = None) -> List[str]:
        """
        执行混合检索，支持metadata过滤
        :param query: 用户查询
        :param top_k: 返回前k个结果
        :param filter_dict: 过滤条件，如 {"layer": "MEDICAL_KNOWLEDGE"}
        :return: 回答列表
        """
        bm25_results = self.bm25.search(query, top_k=5, filter_dict=filter_dict)
        vector_results = self.vector.search(query, top_k=5, filter_dict=filter_dict)
        fused_results = rrf_fusion(bm25_results, vector_results)
        return deduplicate_results(fused_results, self.documents, top_k)


# 初始化基础检索器
base_hybrid_retriever = HybridRetriever(FAQ_KB)


def faq_search(user_text: str) -> Optional[str]:
    """基础混合检索 FAQ"""
    results = base_hybrid_retriever.search(user_text, top_k=1)
    if results:
        return results[0]
    return None


# 测试函数
def test_hybrid_search():
    test_queries = [
        "种植牙多少钱",
        "牙齿缺失怎么办",
        "你们几点开门",
        "推荐一个好医生",
        "洗牙贵吗",
        "正畸周期多长",
    ]
    
    print("基础混合检索测试结果：")
    for query in test_queries:
        result = faq_search(query)
        print(f"Q: {query}")
        print(f"A: {result}")
        print("-" * 50)


if __name__ == "__main__":
    test_hybrid_search()