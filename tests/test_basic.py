"""
基础测试套件 - 仅测试本地功能，不调用LLM
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.intent_classifier import intent_classifier
from app.agent.state_machine import StateMachine, AgentState
from app.agent.core import _extract_slots
from app.agent.faq import base_hybrid_retriever


class TestIntentClassifier(unittest.TestCase):
    """测试意图分类器（仅测试关键词匹配）"""
    
    def test_intent_classification(self):
        """测试各种意图的分类准确性"""
        test_cases = [
            ("我牙疼", "Symptom_Check"),
            ("牙齿松动怎么办", "Symptom_Check"),
            ("牙龈出血", "Symptom_Check"),
            ("什么是种植牙", "Procedure_Explain"),
            ("根管治疗是什么", "Procedure_Explain"),
            ("种植牙多少钱", "Price_Inquiry"),
            ("洗牙贵吗", "Price_Inquiry"),
            ("帮我预约", "Lead_Generation"),
            ("我想挂号", "Lead_Generation"),
            ("医院在哪里", "Logistics_Support"),
            ("营业时间", "Logistics_Support"),
            ("种牙会掉吗", "Risk_Assessment"),
            ("太贵了", "Price_Objection"),
            ("医生资质", "Trust_Verification"),
            ("哪个医生好", "Comparative_Analysis"),
            ("怕疼", "Fear_Relief"),
            ("就诊流程", "Process_Flow"),
        ]
        
        for query, expected_intent in test_cases:
            intent, confidence = intent_classifier.classify(query)
            self.assertEqual(intent, expected_intent, 
                           f"Intent mismatch for '{query}': expected {expected_intent}, got {intent}")
    
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
        self.assertEqual(sm.get_current_state(), AgentState.MEDICAL_KNOWLEDGE)
        
        transitions = [
            ("Symptom_Check", AgentState.MEDICAL_KNOWLEDGE),
            ("Price_Inquiry", AgentState.USER_DECISION),
            ("Lead_Generation", AgentState.BUSINESS_CONVERSION),
            ("Logistics_Support", AgentState.GENERAL_SUPPORT),
            ("RETURN_TO_PREVIOUS", AgentState.BUSINESS_CONVERSION),
        ]
        
        for intent, expected_state in transitions:
            new_state = sm.process_intent(intent, 0.9)
            self.assertEqual(new_state, expected_state,
                           f"State transition failed for {intent}")
    
    def test_slot_management(self):
        """测试槽位管理"""
        sm = StateMachine()
        
        sm.sync_slots({"name": "张三", "phone": "13800138000"})
        slots = sm.get_context().slots
        
        self.assertEqual(slots["name"], "张三")
        self.assertEqual(slots["phone"], "13800138000")
        self.assertIsNone(slots["service_type"])
        
        sm.sync_slots({"name": "李四"})
        slots = sm.get_context().slots
        self.assertEqual(slots["name"], "张三")  # 保持原值


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
    
    def test_not_extract_name_with_prefix(self):
        """测试不提取带前缀的姓名"""
        result = _extract_slots("我叫张三")
        self.assertNotIn("name", result)
        
        result = _extract_slots("我是李四")
        self.assertNotIn("name", result)
    
    def test_extract_name(self):
        """测试提取纯姓名"""
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


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("正在运行基础测试套件")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestIntentClassifier))
    suite.addTests(loader.loadTestsFromTestCase(TestStateMachine))
    suite.addTests(loader.loadTestsFromTestCase(TestSlotExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestFAQRetrieval))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print(f"测试完成: {result.testsRun} 个测试")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    run_tests()