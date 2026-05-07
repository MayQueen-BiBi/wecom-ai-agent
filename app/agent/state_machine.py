from typing import Dict, Optional, List, Any
from enum import Enum

# 状态枚举
from enum import Enum
from typing import Any, Dict, List, Optional

class AgentState(Enum):
    MEDICAL_KNOWLEDGE = "MEDICAL_KNOWLEDGE"    # 医学层
    USER_DECISION = "USER_DECISION"            # 决策层
    OBJECTION_HANDLING = "OBJECTION_HANDLING"  # 异议处理
    BUSINESS_CONVERSION = "BUSINESS_CONVERSION" # 转化层
    GENERAL_SUPPORT = "GENERAL_SUPPORT"        # 支持层（插件式）
    SUCCESS_FINISH = "SUCCESS_FINISH"          # 结束

# --- 逻辑配置解耦 ---

# 哪些意图属于“临时插件”，处理完必须弹回原状态
TEMPORARY_INTENTS = {
    "Logistics_Support": AgentState.GENERAL_SUPPORT,
    "Out_of_Scope": AgentState.GENERAL_SUPPORT,
}

# 核心业务转移矩阵 (去掉了冗余的插件意图)
CORE_TRANSITIONS = {
    AgentState.MEDICAL_KNOWLEDGE: {
        "Price_Inquiry": AgentState.USER_DECISION,
        "Comparative_Analysis": AgentState.USER_DECISION,
        "Lead_Generation": AgentState.BUSINESS_CONVERSION,
        "Fear_Relief": AgentState.OBJECTION_HANDLING,
    },
    AgentState.USER_DECISION: {
        "Symptom_Check": AgentState.MEDICAL_KNOWLEDGE,
        "Lead_Generation": AgentState.BUSINESS_CONVERSION,
        "Price_Objection": AgentState.OBJECTION_HANDLING,
    },
    AgentState.OBJECTION_HANDLING: {
        "Lead_Generation": AgentState.BUSINESS_CONVERSION,
        "Procedure_Explain": AgentState.MEDICAL_KNOWLEDGE,
    },
    AgentState.BUSINESS_CONVERSION: {
        "Price_Inquiry": AgentState.USER_DECISION, # 挂起转化，去解释价格
        "Fear_Relief": AgentState.OBJECTION_HANDLING,
    }
}

class ConversationContext:
    def __init__(self):
        # 1. 使用栈管理状态：栈顶永远是当前状态
        self.state_stack: List[AgentState] = [AgentState.MEDICAL_KNOWLEDGE]
        self.intent_history: List[tuple] = []
        
        # 2. 槽位管理
        self.slots = {
            "name": None, "phone": None, "service_type": None, "time_slot": None
        }
        
        # 3. 任务恢复区：存储挂起时的槽位快照
        self.suspended_slots: Optional[Dict] = None
        self.CONFIDENCE_THRESHOLD = 0.6 # 算法门控

    @property
    def current_state(self) -> AgentState:
        return self.state_stack[-1]

    def transition(self, intent: str, confidence: float = 1.0) -> AgentState:
        """
        基于栈结构的状态转移引擎
        """
        # 低置信度拦截
        if confidence < self.CONFIDENCE_THRESHOLD:
            return self.current_state

        self.intent_history.append((intent, confidence))
        old_state = self.current_state

        # --- 策略 A: 全局插件拦截 (入栈逻辑) ---
        if intent in TEMPORARY_INTENTS:
            target_state = TEMPORARY_INTENTS[intent]
            if target_state != old_state:
                # 如果从转化层跳出，备份当前槽位
                if old_state == AgentState.BUSINESS_CONVERSION:
                    self.suspended_slots = self.slots.copy()
                self.state_stack.append(target_state)
            return self.current_state

        # --- 策略 B: 业务状态转移 (矩阵逻辑) ---
        # 检查是否是“返回”指令 (通常由 Response Generator 根据上下文判断后传入)
        if intent == "RETURN_TO_PREVIOUS" or intent == "Task_Finished":
            if len(self.state_stack) > 1:
                self.state_stack.pop()
                # 如果回到了转化层，执行槽位合并
                if self.current_state == AgentState.BUSINESS_CONVERSION and self.suspended_slots:
                    self.slots.update({k: v for k, v in self.suspended_slots.items() if v})
                    self.suspended_slots = None
            return self.current_state

        # 查表寻找转移目标
        target_state = CORE_TRANSITIONS.get(old_state, {}).get(intent)

        # --- 策略 C: 状态演进与回溯 ---
        if target_state and target_state != old_state:
            # 特殊逻辑：如果从转化层主动跳往决策/医学层，视为“挂起”而非“丢弃”
            if old_state == AgentState.BUSINESS_CONVERSION:
                self.suspended_slots = self.slots.copy()
                self.state_stack.append(target_state) # 压栈，处理完还能回来
            else:
                # 普通平级跳转，替换栈顶
                self.state_stack[-1] = target_state
        
        return self.current_state

    # --- 槽位操作支持增量合并 ---
    def update_slots(self, new_data: Dict[str, Any]):
        """增量更新槽位，不覆盖已有非空值"""
        for k, v in new_data.items():
            if k in self.slots and v and self.slots[k] is None:
                self.slots[k] = v

    def get_context_summary(self) -> Dict:
        return {
            "current_state": self.current_state.value,
            "stack_depth": len(self.state_stack),
            "stack_trace": [s.value for s in self.state_stack],
            "slots": self.slots,
            "is_suspended": self.suspended_slots is not None
        }

    def set_slot(self, key: str, value: Any):
        """设置槽位"""
        if key in self.slots:
            self.slots[key] = value

    def get_slot(self, key: str) -> Any:
        """获取槽位"""
        return self.slots.get(key)

    def is_slot_filled(self, key: str) -> bool:
        """检查槽位是否填充"""
        return self.slots.get(key) is not None


class StateMachine:
    """
    状态机控制中心：对话系统的“中控大脑”
    负责协调意图识别后的业务路由、检索约束生成和槽位决策。
    """
    
    def __init__(self):
        self.context = ConversationContext()
    
    def process_intent(self, intent: str, confidence: float = 0.0) -> AgentState:
        """
        处理意图并驱动状态机演进
        """
        # 1. 执行核心状态迁移（利用 Context 的栈逻辑）
        new_state = self.context.transition(intent, confidence)
        
        # 2. 算法埋点：可以在此处记录状态跳变日志，便于 Bad-case 分析
        return new_state

    def get_retrieval_strategy(self) -> Dict[str, Any]:
        """
        【算法核心】根据当前状态栈，生成动态检索策略。
        不仅返回 layer 过滤，还返回检索权重（Top-K）
        """
        state = self.context.current_state
        
        # 默认路由映射
        layer_mapping = {
            AgentState.MEDICAL_KNOWLEDGE: "MEDICAL_KNOWLEDGE",
            AgentState.USER_DECISION: "USER_DECISION",
            AgentState.OBJECTION_HANDLING: "OBJECTION_HANDLING",
            AgentState.BUSINESS_CONVERSION: "BUSINESS_CONVERSION",
            AgentState.GENERAL_SUPPORT: "GENERAL_SUPPORT"
        }

        strategy = {
            "filter": {"layer": layer_mapping.get(state, "MEDICAL_KNOWLEDGE")},
            "top_k": 3,
            "search_type": "hybrid" # 默认混合检索
        }

        # 针对转化层的特殊检索策略：不仅搜转化层，还要带上通用信息
        if state == AgentState.BUSINESS_CONVERSION:
            strategy["top_k"] = 5
            # 允许扩大召回范围，防止转化时用户问及通用支持问题
            strategy["filter"] = {"layer": ["BUSINESS_CONVERSION", "GENERAL_SUPPORT"]}
            
        return strategy

    def get_action_guidance(self) -> Dict[str, Any]:
        """
        【对话决策】推断 LLM 下一步的动作逻辑。
        告诉生成层：现在是该科普、该填槽、还是该处理异议。
        """
        state = self.context.current_state
        
        # 基础动作定义
        guidance = {
            "persona_focus": "professional_expert",
            "must_include_slots": False,
            "is_interrupted": len(self.context.state_stack) > 1
        }

        if state == AgentState.BUSINESS_CONVERSION:
            guidance.update({
                "persona_focus": "warm_assistant",
                "must_include_slots": True,
                "missing_slots": [k for k, v in self.context.slots.items() if v is None]
            })
        elif state == AgentState.OBJECTION_HANDLING:
            guidance["persona_focus"] = "empathetic_counselor"
            
        return guidance

    # --- 槽位代理操作 ---

    def sync_slots(self, extracted_slots: Dict[str, Any]):
        """同步从 LLM 提取到的槽位数据"""
        self.context.update_slots(extracted_slots)

    def is_task_complete(self) -> bool:
        """判断当前阶段任务是否完成（如预约信息是否全了）"""
        if self.context.current_state == AgentState.BUSINESS_CONVERSION:
            # 至少要有姓名和电话才算初步完成
            return self.context.slots.get("name") and self.context.slots.get("phone")
        return False

    def reset(self):
        """重置状态机"""
        self.context = ConversationContext()

    # --- 兼容旧接口 ---
    def get_current_state(self) -> AgentState:
        """获取当前状态（兼容旧接口）"""
        return self.context.current_state

    def get_context(self) -> ConversationContext:
        """获取对话上下文（兼容旧接口）"""
        return self.context

    def fill_slot(self, key: str, value: Any):
        """填充槽位（兼容旧接口，使用增量更新）"""
        self.context.update_slots({key: value})

    def get_layer_filter(self) -> Optional[Dict[str, str]]:
        """获取检索过滤条件（兼容旧接口）"""
        strategy = self.get_retrieval_strategy()
        filter_dict = strategy.get("filter", {})
        # 如果是列表形式，转为字符串（兼容旧的filter_dict格式）
        if isinstance(filter_dict.get("layer"), list):
            return {"layer": filter_dict["layer"][0]}
        return filter_dict

# 全局单例
state_machine = StateMachine()

# 测试函数
def test_state_machine():
    print("=== 测试状态机 ===")
    
    # 模拟对话流程
    test_cases = [
        ("Symptom_Check", 0.9),      # 症状诊断 -> MEDICAL_KNOWLEDGE
        ("Price_Inquiry", 0.9),      # 价格询问 -> USER_DECISION
        ("Lead_Generation", 0.9),    # 预约引导 -> BUSINESS_CONVERSION
        ("Logistics_Support", 0.9),  # 地址询问 -> GENERAL_SUPPORT (插件式)
        ("Lead_Generation", 0.9),    # 回到预约 -> BUSINESS_CONVERSION
    ]
    
    sm = StateMachine()
    
    for intent, confidence in test_cases:
        prev_state = sm.get_current_state()
        new_state = sm.process_intent(intent, confidence)
        print(f"Intent: {intent}")
        print(f"   From: {prev_state.value} -> To: {new_state.value}")
        print()
    
    # 打印上下文摘要
    print("=== 上下文摘要 ===")
    summary = sm.get_context().get_context_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    test_state_machine()