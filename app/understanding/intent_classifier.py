from typing import Dict, Optional, List, Tuple
import re
import json
import requests
import logging
from app.config.settings import QWEN_API_KEY

logger = logging.getLogger(__name__)

QWEN_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

# 12个核心意图定义
INTENT_DEFINITIONS = {
    # --- 认知探索类 (Inquiry & Education) ---
    "Symptom_Check": {
        "description": "症状诊断：用户描述具体的生理不适或异常现象，核心诉求是'我这是怎么了'或'该怎么办'。",
        "logic": "主语通常是自身部位（牙龈、智齿），动词是感受（疼、肿、出血）。",
        "keywords": ["疼", "痛", "出血", "肿", "发炎", "松动", "敏感", "溃疡", "口臭", "不舒服"],
        "examples": ["我牙疼怎么办", "牙龈出血一周了", "后槽牙有个洞", "嘴里长溃疡了"]
    },
    "Procedure_Explain": {
        "description": "方案科普：对特定医学术语、治疗手段的定义、原理或必要性进行询问。",
        "logic": "关键特征是'是什么'、'为什么'。注意：询问'怎么做'也归于此类，除非涉及具体时间流程。",
        "keywords": ["什么是", "是什么", "什么叫", "什么意思", "解释一下", "科普", "原理", "怎么做"],
        "examples": ["什么是根管治疗", "隐形矫正原理是什么", "为什么要拔智齿", "补牙是怎么补的"]
    },
    "Process_Flow": {
        "description": "流程咨询：关注治疗的'时间轴'，包括时长、次数、频率及术前术后注意事项。",
        "logic": "核心词是'多久'、'几次'。区分于科普：科普问原理，流程问时间。",
        "keywords": ["几次", "周期", "时间", "复诊", "复查", "多久", "多长时间"],
        "examples": ["种植牙要来几次", "正畸一般要戴多久牙套", "拔牙后多久能吃饭", "复诊频率"]
    },

    # --- 决策对比类 (Decision Support) ---
    "Price_Inquiry": {
        "description": "价格询盘：对客观价格、收费标准、医保政策的单纯询问。",
        "logic": "核心是'多少钱'。注意：如果带有情绪嫌贵，应划入 Price_Objection。",
        "keywords": ["多少钱", "价格", "费用", "贵吗", "收费", "医保", "报销"],
        "examples": ["全口种植大概多少钱", "洗牙能用医保吗", "正畸收费标准", "挂号费多少"]
    },
    "Comparative_Analysis": {
        "description": "选型对比：在不同品牌、材料、技术方案之间进行优劣、性价比的权衡。",
        "logic": "特征是出现两个及以上实体（国产vs进口、全瓷vs烤瓷、金属vs隐形）。",
        "keywords": ["对比", "哪个好", "选哪个", "vs", "国产", "进口", "推荐"],
        "examples": ["国产和进口植体哪个好", "隐形和金属矫正怎么选", "全瓷牙和烤瓷牙区别"]
    },
    "Risk_Assessment": {
        "description": "风险评估：用户表达对治疗安全性、后遗症、持久性或失败可能的担忧。",
        "logic": "核心是'稳不稳'、'会坏吗'。特征词：掉、松动、失败、后遗症、副作用。",
        "keywords": ["风险", "后遗症", "成功率", "安全吗", "会掉吗", "副作用"],
        "examples": ["种牙会掉吗", "正畸会有黑三角吗", "全瓷牙能用多少年", "失败了怎么办"]
    },

    # --- 异议处理类 (Objection Handling) ---
    "Fear_Relief": {
        "description": "恐惧安抚：心理层面的担忧，主要是对'痛感'和'诊疗环境'的畏惧。",
        "logic": "即使问'疼不疼'，其本质也是寻求安抚。区分于风险：风险是问效果，恐惧是问感受。",
        "keywords": ["怕疼", "疼吗", "无痛", "麻醉", "声音", "害怕", "紧张"],
        "examples": ["治疗会疼吗", "我特别怕打麻药", "有没有无痛种植", "钻牙的声音很可怕"]
    },
    "Price_Objection": {
        "description": "价格异议：对价格的主观反馈，如嫌贵、要折扣、对比其他机构价格。",
        "logic": "带有主观情绪或砍价意图。特征词：太贵了、能便宜点吗、优惠、活动。",
        "keywords": ["太贵", "便宜点", "优惠", "打折", "太贵了", "能便宜吗"],
        "examples": ["这也太贵了吧", "别家才卖三千", "有没有团购优惠", "学生证打折吗"]
    },
    "Trust_Verification": {
        "description": "信任背书：对医生专业度、医院硬件、过往案例的考察。",
        "logic": "核心是'凭什么信你'。特征词：医生、专家、院长、资质、案例、靠谱吗。",
        "keywords": ["医生", "专家", "资质", "案例", "荣誉", "证书", "职称"],
        "examples": ["医生资质怎么样", "谁给我做手术", "能看下之前的案例吗", "医院是公立还是私立"]
    },

    # --- 业务转化类 (Action Oriented) ---
    "Lead_Generation": {
        "description": "预约引导：明确表达就诊意愿、询问挂号方式或要求人工介入。",
        "logic": "行动导向。特征词：预约、挂号、想去看看、安排、怎么走流程。",
        "keywords": ["预约", "挂号", "看牙", "就诊", "安排时间", "帮我预约"],
        "examples": ["帮我预约明天的号", "我想去面诊一下", "怎么挂号", "现在有医生吗"]
    },
    "Logistics_Support": {
        "description": "就诊保障：询问医院物理位置、营业时间、交通、停车等配套信息。",
        "logic": "核心是'怎么去'和'什么时候去'。注意：医保卡能否现场使用也可归于此。",
        "keywords": ["地址", "位置", "停车", "营业时间", "几点开门", "停车"],
        "examples": ["医院在哪里", "周末开门吗", "有停车场吗", "坐地铁几号线到"]
    },
    "Out_of_Scope": {
        "description": "兜底处理：完全脱离牙科医疗及医院服务范畴的话题。",
        "logic": "垃圾信息、通用闲聊（天气、政治、日常）。",
        "keywords": [],
        "examples": ["今天天气怎么样", "你会唱歌吗", "帮我写个代码"]
    }
}

# 强意图关键词（触发确定性分类）
STRONG_INTENT_KEYWORDS = {
    "Lead_Generation": [
        "预约",
        "帮我预约",
        "安排时间",
        "我想挂号",
        "我要挂号",
        "去挂号",
    ],
    "Logistics_Support": [
        "地址",
        "位置",
        "在哪里",
        "营业时间",
        "几点开门",
        "停车",
    ],
    "Price_Inquiry": ["多少钱", "价格", "费用", "贵吗"],
    # 情绪/恐惧先于泛症状词「疼」，避免「怕疼」被误判为 Symptom_Check
    "Fear_Relief": ["怕疼", "疼吗", "无痛", "麻醉", "害怕"],
    "Symptom_Check": ["疼", "痛", "出血", "松动"],
    "Procedure_Explain": [
        "什么是",
        "是什么",
        "什么叫",
        "什么意思",
        "解释一下",
        "原理",
        "科普",
        "怎么做",
    ],
    "Process_Flow": [
        "就诊流程",
        "怎么挂号",
        "流程",
        "几次",
        "周期",
        "时间",
        "复诊",
        "多久",
    ],
    "Comparative_Analysis": [
        "哪个医生好",
        "哪位医生好",
        "哪个医生",
        "对比",
        "哪个好",
        "选哪个",
        "国产",
        "进口",
    ],
    "Risk_Assessment": ["风险", "后遗症", "成功率", "安全吗", "会掉吗", "副作用"],
    "Price_Objection": ["太贵", "便宜点", "优惠", "打折"],
    "Trust_Verification": ["医生", "专家", "资质", "案例", "职称"],
}


class IntentClassifier:
    """意图分类器：将用户话语转化为12个意图节点"""
    
    def __init__(self):
        self.qwen_url = QWEN_URL
    
    def _keyword_based_classify(self, query: str) -> Optional[Tuple[str, float]]:
        """
        基于关键词的快速分类（强意图词匹配）
        :param query: 用户查询
        :return: (意图名, 置信度) 如果匹配到强意图词
        """
        for intent, keywords in STRONG_INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in query:
                    # 根据匹配关键词数量计算置信度
                    match_count = sum(1 for k in keywords if k in query)
                    confidence = min(0.95, 0.7 + match_count * 0.1)
                    return (intent, confidence)
        return None
    
    def _llm_based_classify(self, query: str) -> Tuple[str, float]:
        """
        基于LLM的意图分类
        :param query: 用户查询
        :return: (意图名, 置信度)
        """
        if not QWEN_API_KEY:
            return ("Out_of_Scope", 0.5)
        
        # 构建few-shot样本
        examples = []
        for intent, config in INTENT_DEFINITIONS.items():
            for example in config["examples"][:2]:
                examples.append(f'"{example}" -> {intent}')
        
        examples_text = "\n".join(examples)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {QWEN_API_KEY}"
        }
        
        # 建议在外部先处理好 definitions_text，加入逻辑说明(logic)
        definitions_with_logic = {
            k: f"{v['description']} | 判定逻辑: {v.get('logic', '无')}" 
            for k, v in INTENT_DEFINITIONS.items()
        }

        payload = {
            "model": "qwen-flash",
            "input": {
                "messages": [
                    {
                        "role": "system",
                        "content": f"""
        你是一个高精度的牙科医疗客服意图解析引擎。你的任务是将用户输入映射到预定义的意图标签中。

        ### 1. 意图图谱与判定逻辑
        {json.dumps(definitions_with_logic, ensure_ascii=False, indent=2)}

        ### 2. 核心分类准则 (算法规则)
        - **领域优先性**：只要涉及牙齿、口腔、手术方案、医生、价格，严禁分类为 Out_of_Scope。
        - **差异化判定**：
            - 区分 [Price_Inquiry] (问价) 与 [Price_Objection] (嫌贵/要优惠)。
            - 区分 [Procedure_Explain] (问原理/是什么) 与 [Process_Flow] (问时间/几次/多久)。
            - 区分 [Symptom_Check] (描述痛苦寻求判断) 与 [Fear_Relief] (表达害怕寻求安慰)。
        - **上下文推断**：如果用户只说"国产的呢？"，结合意图图谱，这应属于 [Comparative_Analysis]。

        ### 3. 负采样防御
        - 仅当用户谈论天气、政治、娱乐等与"看牙/医疗"完全无关的话题时，才允许输出 Out_of_Scope。

        ### 4. 推理要求
        - 请先在内部进行思维链(CoT)分析：用户的关键词是什么 -> 属于动作、认知还是情绪 -> 匹配哪个定义。
        - 最终仅输出 JSON。

        输出格式示例：{{"intent": "意图名称", "confidence": 0.95}}
        """
                    },
                    {
                        "role": "user",
                        "content": f"用户问题：{query}"
                    }
                ]
            },
            "parameters": {
                "result_format": "message",
                "temperature": 0.1,  # 降低随机性，对分类任务至关重要
                "top_p": 0.8
            }
        }
        
        try:
            resp = requests.post(self.qwen_url, headers=headers, json=payload, timeout=5)
            if resp.status_code == 200:
                result = resp.json()
                if "output" in result:
                    content = result["output"]["choices"][0]["message"]["content"].strip()
                    try:
                        result_dict = json.loads(content)
                        intent = result_dict.get("intent", "Out_of_Scope")
                        confidence = min(1.0, max(0.0, result_dict.get("confidence", 0.5)))
                        return (intent, confidence)
                    except json.JSONDecodeError:
                        pass
            elif resp.status_code == 401:
                logger.warning("QWEN_API_KEY is blocked or invalid")
        except Exception as e:
            logger.error(f"Intent classification error: {e}")
        
        return ("Out_of_Scope", 0.5)
    
    def classify(self, query: str) -> Tuple[str, float]:
        """
        意图分类主函数：先尝试关键词匹配，再使用LLM
        :param query: 用户查询
        :return: (意图名, 置信度)
        """
        # 步骤1：检查是否为空或无效输入
        if not query or not query.strip():
            return ("Out_of_Scope", 0.0)
        
        query = query.strip()
        
        # 步骤2：强意图关键词匹配（快速路径）
        keyword_result = self._keyword_based_classify(query)
        if keyword_result:
            intent, confidence = keyword_result
            if confidence >= 0.8:
                return (intent, confidence)
        
        # 步骤3：LLM分类（兜底）
        intent, confidence = self._llm_based_classify(query)
        
        # 步骤4：关键词补偿逻辑（校准）
        return self._calibrate_intent(query, intent, confidence)
    
    def _calibrate_intent(self, query: str, intent: str, confidence: float) -> Tuple[str, float]:
        """
        关键词补偿逻辑：对LLM分类结果进行校准
        :param query: 用户查询
        :param intent: LLM分类的意图
        :param confidence: LLM分类的置信度
        :return: 校准后的(意图名, 置信度)
        """
        # 如果已经是高置信度，直接返回
        if confidence >= 0.9:
            return (intent, confidence)
        
        # 检查是否有强意图词被遗漏
        for strong_intent, keywords in STRONG_INTENT_KEYWORDS.items():
            if any(kw in query for kw in keywords):
                # 如果强意图词存在但LLM没识别到，进行校准
                if intent != strong_intent:
                    # 混合置信度
                    new_confidence = (confidence + 0.8) / 2
                    return (strong_intent, new_confidence)
        
        return (intent, confidence)
    
    def get_intent_info(self, intent: str) -> Optional[Dict]:
        """
        获取意图详细信息
        :param intent: 意图名称
        :return: 意图配置字典
        """
        return INTENT_DEFINITIONS.get(intent)


# 全局意图分类器实例
intent_classifier = IntentClassifier()


# 测试函数
def test_intent_classifier():
    print("=== 测试意图分类器 ===")
    
    test_cases = [
        "我牙疼怎么办",          # Symptom_Check
        "什么是根管治疗",         # Procedure_Explain
        "种植牙要来几次",         # Process_Flow
        "全口种植多少钱",         # Price_Inquiry
        "国产和进口哪个好",       # Comparative_Analysis
        "种牙会掉吗",            # Risk_Assessment
        "治疗会疼吗",            # Fear_Relief
        "太贵了",               # Price_Objection
        "医生资质怎么样",         # Trust_Verification
        "帮我预约",             # Lead_Generation
        "医院在哪里",            # Logistics_Support
        "今天天气怎么样",         # Out_of_Scope
    ]
    
    for query in test_cases:
        intent, confidence = intent_classifier.classify(query)
        print(f"Q: {query}")
        print(f"   Intent: {intent}, Confidence: {confidence:.2f}")
        print()


if __name__ == "__main__":
    test_intent_classifier()
