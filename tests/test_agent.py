"""
系统测试套件 - 用于验证 wecom-ai-agent 的各项功能
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.core import run_agent, get_metrics, _extract_slots
from app.agent.intent_classifier import intent_classifier
from app.agent.state_machine import StateMachine, AgentState
from app.agent.semantic_cache import semantic_cache
from app.agent.faq import base_hybrid_retriever, FAQ_KB


class TestIntentClassifier(unittest.TestCase):
    """测试意图分类器"""
    
    def test_intent_classification(self):
        """测试各种意图的分类准确性"""
        test_cases = [
            ("我牙疼", "Symptom_Check"),
            ("牙齿松动怎么办", "Symptom_Check"),
            ("牙龈出血", "Symptom_Check"),
            ("什么是种植牙", "Procedure_Explain"),
            ("根管治疗是什么", "Procedure_Explain"),
            ("正畸是怎么做的", "Procedure_Explain"),
            ("种植牙多少钱", "Price_Inquiry"),
            ("洗牙贵吗", "Price_Inquiry"),
            ("拔牙费用", "Price_Inquiry"),
            ("帮我预约", "Lead_Generation"),
            ("我想挂号", "Lead_Generation"),
            ("安排时间", "Lead_Generation"),
            ("医院在哪里", "Logistics_Support"),
            ("营业时间", "Logistics_Support"),
            ("停车方便吗", "Logistics_Support"),
            ("种牙会掉吗", "Risk_Assessment"),
            ("风险大吗", "Risk_Assessment"),
            ("成功率多少", "Risk_Assessment"),
            ("太贵了", "Price_Objection"),
            ("便宜点", "Price_Objection"),
            ("医生资质", "Trust_Verification"),
            ("专家介绍", "Trust_Verification"),
            ("哪个医生好", "Comparative_Analysis"),
            ("种植牙和正畸哪个好", "Comparative_Analysis"),
            ("怕疼", "Fear_Relief"),
            ("害怕", "Fear_Relief"),
            ("就诊流程", "Process_Flow"),
            ("怎么挂号", "Process_Flow"),
        ]
        
        for query, expected_intent in test_cases:
            intent, confidence = intent_classifier.classify(query)
            self.assertEqual(intent, expected_intent, 
                           f"Intent mismatch for '{query}': expected {expected_intent}, got {intent}")
            self.assertGreaterEqual(confidence, 0.6,
                                  f"Confidence too low for '{query}': {confidence}")
    
    def test_out_of_scope(self):
        """测试超出范围的问题"""
        out_of_scope_queries = [
            "天气怎么样",
            "今天吃什么",
            "新闻头条",
            "股票行情",
        ]
        
        for query in out_of_scope_queries:
            intent, confidence = intent_classifier.classify(query)
            self.assertEqual(intent, "Out_of_Scope")


class TestStateMachine(unittest.TestCase):
    """测试状态机"""
    
    def test_state_transitions(self):
        """测试状态转换逻辑"""
        sm = StateMachine()
        
        # 初始状态应该是 MEDICAL_KNOWLEDGE
        self.assertEqual(sm.get_current_state(), AgentState.MEDICAL_KNOWLEDGE)
        
        # 测试状态转换
        transitions = [
            ("Symptom_Check", AgentState.MEDICAL_KNOWLEDGE),    # 保持在医学层
            ("Price_Inquiry", AgentState.USER_DECISION),         # 转到决策层
            ("Lead_Generation", AgentState.BUSINESS_CONVERSION), # 转到转化层
            ("Logistics_Support", AgentState.GENERAL_SUPPORT),   # 插件式状态（压栈）
            ("RETURN_TO_PREVIOUS", AgentState.BUSINESS_CONVERSION), # 弹出插件状态返回转化层
        ]
        
        for intent, expected_state in transitions:
            new_state = sm.process_intent(intent, 0.9)
            self.assertEqual(new_state, expected_state,
                           f"State transition failed for {intent}")
    
    def test_slot_management(self):
        """测试槽位管理"""
        sm = StateMachine()
        
        # 测试增量更新槽位
        sm.sync_slots({"name": "张三", "phone": "13800138000"})
        slots = sm.get_context().slots
        
        self.assertEqual(slots["name"], "张三")
        self.assertEqual(slots["phone"], "13800138000")
        self.assertIsNone(slots["service_type"])
        self.assertIsNone(slots["time_slot"])
        
        # 测试不覆盖已有值
        sm.sync_slots({"name": "李四"})
        slots = sm.get_context().slots
        self.assertEqual(slots["name"], "张三")  # 应该保持原值


class TestSlotExtractor(unittest.TestCase):
    """测试槽位提取器"""
    
    def test_extract_phone(self):
        """测试手机号提取"""
        result = _extract_slots("我的手机号是13812345678")
        self.assertEqual(result["phone"], "13812345678")
        
        result = _extract_slots("电话：13987654321")
        self.assertEqual(result["phone"], "13987654321")
    
    def test_extract_service(self):
        """测试服务类型提取"""
        result = _extract_slots("我想预约种植牙")
        self.assertEqual(result["service_type"], "种植牙")
        
        result = _extract_slots("正畸多少钱")
        self.assertEqual(result["service_type"], "正畸")
    
    def test_extract_name(self):
        """测试姓名提取"""
        result = _extract_slots("我叫张三")
        self.assertNotIn("name", result)  # 不应该提取，因为包含"我叫"
        
        result = _extract_slots("张三")
        self.assertEqual(result["name"], "张三")


class TestFAQRetrieval(unittest.TestCase):
    """测试FAQ检索"""
    
    def test_basic_search(self):
        """测试基础检索功能"""
        queries = [
            ("种植牙", ["种植牙通常分为检查评估"]),
            ("洗牙", ["洁牙主要用于清除牙结石"]),
            ("价格", ["不同项目费用会根据检查结果"]),
        ]
        
        for query, expected_contains in queries:
            results = base_hybrid_retriever.search(query, top_k=1)
            self.assertTrue(len(results) > 0, f"No results for '{query}'")
            for expected in expected_contains:
                self.assertIn(expected, results[0], 
                             f"Expected '{expected}' not found in result")


class TestSemanticCache(unittest.TestCase):
    """测试语义缓存"""
    
    def setUp(self):
        """测试前清空缓存"""
        semantic_cache.clear()
    
    def test_cache_set_get(self):
        """测试缓存设置和获取"""
        semantic_cache.set("[Price_Inquiry] 种植牙多少钱", "价格是10000元", {})
        result = semantic_cache.get("[Price_Inquiry] 种植牙多少钱")
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "价格是10000元")
    
    def test_cache_intent_discrimination(self):
        """测试意图区分"""
        semantic_cache.set("[Procedure_Explain] 什么是种植牙", "种植牙是修复方式", {})
        result = semantic_cache.get("[Price_Inquiry] 种植牙多少钱")
        
        # 不同意图不应该命中缓存
        self.assertIsNone(result)
    
    def test_cache_similarity(self):
        """测试语义相似度匹配"""
        semantic_cache.set("[Price_Inquiry] 种植牙多少钱", "价格是10000元", {})
        
        # 完全相同的查询应该命中
        result = semantic_cache.get("[Price_Inquiry] 种植牙多少钱")
        self.assertIsNotNone(result)
        
        # 非常相似的查询应该命中
        result = semantic_cache.get("[Price_Inquiry] 种植牙价格")
        self.assertIsNotNone(result)
        
        # 不相关的查询不应该命中
        result = semantic_cache.get("[Price_Inquiry] 洗牙多少钱")
        self.assertIsNone(result)


class TestEndToEnd(unittest.TestCase):
    """端到端测试"""
    
    def test_conversation_flow(self):
        """测试完整对话流程"""
        user_id = "test_user_e2e"
        
        # 测试症状咨询
        response = run_agent(user_id, "我牙疼")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        # 测试价格咨询
        response = run_agent(user_id, "种植牙多少钱")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        # 测试预约引导
        response = run_agent(user_id, "帮我预约")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
    
    def test_metrics(self):
        """测试监控指标"""
        # 清除之前的指标
        global metrics
        metrics = {
            "intent_distribution": {},
            "state_transitions": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "total_queries": 0
        }
        
        user_id = "test_user_metrics"
        run_agent(user_id, "我牙疼")
        
        metrics_result = get_metrics()
        self.assertIn("total_queries", metrics_result)
        self.assertIn("cache_hit_rate", metrics_result)
        self.assertIn("intent_distribution", metrics_result)


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("正在运行 wecom-ai-agent 测试套件")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestIntentClassifier))
    suite.addTests(loader.loadTestsFromTestCase(TestStateMachine))
    suite.addTests(loader.loadTestsFromTestCase(TestSlotExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestFAQRetrieval))
    suite.addTests(loader.loadTestsFromTestCase(TestSemanticCache))
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEnd))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print(f"测试完成: {result.testsRun} 个测试")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    run_all_tests()
