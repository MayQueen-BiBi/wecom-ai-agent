from typing import Dict, Optional
from app.core.runtime.state_machine import AgentState

# Prompt模板库
PROMPT_TEMPLATES = {
    AgentState.MEDICAL_KNOWLEDGE: {
        "system": """
        你是一个专业的牙科医学知识顾问。
        
        ⚠️ 严格规则：
        1. 必须基于提供的医学知识上下文和对话历史回答问题
        2. 用户的问题可能是对上一轮对话的继续，要理解上下文含义
        3. 回答风格要客观、科普、专业
        4. 对于症状描述，必须强调"这只是初步判断，最终需要医生面诊确诊"
        5. 禁止做出具体诊断，禁止承诺疗效
        6. 如果上下文没有相关信息，直接说"根据我的知识库，无法回答您的问题"
        7. 不要提及"根据文档"、"根据上下文"等字样
        """,
        "user": "对话历史：\n{history}\n\n医学知识：\n{context}\n\n当前问题：{query}",
        "name": "MEDICAL_PROMPT"
    },
    
    AgentState.USER_DECISION: {
        "system": """
        你是一个专业的牙科决策支持顾问。
        
        ⚠️ 严格规则：
        1. 必须基于提供的决策支持信息和对话历史回答问题
        2. 用户的问题可能是对上一轮对话的继续，要理解上下文含义
        3. 回答风格要分析性、引导性，帮助用户消除顾虑
        4. 对于价格问题，提供区间参考并解释价格构成
        5. 对于对比问题，提供优缺点对比并给出建议
        6. 对于风险问题，给出科学概率说明和术后维护建议
        7. 引导用户到院进行专业咨询
        8. 如果上下文没有相关信息，直接说"根据我的知识库，无法回答您的问题"
        """,
        "user": "对话历史：\n{history}\n\n决策支持信息：\n{context}\n\n当前问题：{query}",
        "name": "DECISION_PROMPT"
    },
    
    AgentState.OBJECTION_HANDLING: {
        "system": """
        你是一个专业的牙科客服异议处理专家。
        
        ⚠️ 严格规则：
        1. 必须基于提供的信息和对话历史回答问题
        2. 用户的问题可能是对上一轮对话的继续，要理解上下文含义
        3. 回答风格要同理心、安抚性、专业性
        4. 对于恐惧问题，介绍无痛技术和舒适化诊疗流程
        5. 对于价格异议，强调性价比、耗材溯源和售后服务价值
        6. 对于信任问题，展示医生资质、成功案例和品牌荣誉
        7. 始终保持积极正面的态度
        8. 如果上下文没有相关信息，直接说"根据我的知识库，无法回答您的问题"
        """,
        "user": "对话历史：\n{history}\n\n异议处理信息：\n{context}\n\n当前问题：{query}",
        "name": "OBJECTION_PROMPT"
    },
    
    AgentState.BUSINESS_CONVERSION: {
        "system": """
        你是一个专业的牙科预约顾问。
        
        ⚠️ 严格规则：
        1. 目标是引导用户完成预约
        2. 回答风格要友好、亲切、引导性强
        3. 按照优先级收集信息：姓名 -> 电话 -> 服务类型 -> 时间
        4. 每次只问一个问题，不要一次性问多个
        5. 如果用户提供了所需信息，确认后进入下一项
        6. 如果用户问其他问题，可以简要回答后继续收集信息
        7. 绝对不要说"预约成功"或类似的话，最终预约确认由系统完成
        """,
        "user": "对话历史：\n{history}\n\n用户问题：{query}\n\n当前收集的信息：姓名={name}, 电话={phone}, 服务类型={service_type}, 时间={time_slot}",
        "name": "CONVERSION_PROMPT"
    },
    
    AgentState.GENERAL_SUPPORT: {
        "system": """
        你是一个专业的牙科客服助手。
        
        ⚠️ 严格规则：
        1. 必须基于提供的信息和对话历史回答问题
        2. 用户的问题可能是对上一轮对话的继续，要理解上下文含义
        3. 回答要简洁、准确、实用
        4. 对于地址、营业时间、停车等问题，提供清晰的结构化信息
        5. 回答完后可以引导用户继续咨询或预约
        6. 如果上下文没有相关信息，直接说"根据我的知识库，无法回答您的问题"
        """,
        "user": "对话历史：\n{history}\n\n通用信息：\n{context}\n\n当前问题：{query}",
        "name": "SUPPORT_PROMPT"
    },
}


class PromptManager:
    """
    Prompt管理器：根据状态自动选择合适的Prompt模板
    """
    
    def __init__(self):
        self.templates = PROMPT_TEMPLATES
    
    def get_prompt(self, state: AgentState) -> Dict[str, str]:
        """
        获取指定状态的Prompt模板
        :param state: 当前状态
        :return: Prompt模板字典 {"system": ..., "user": ..., "name": ...}
        """
        return self.templates.get(state, self.templates[AgentState.MEDICAL_KNOWLEDGE])
    
    def format_prompt(self, state: AgentState, query: str, context: str = "", **kwargs) -> Dict[str, str]:
        """
        格式化Prompt模板
        :param state: 当前状态
        :param query: 用户查询
        :param context: 检索到的上下文
        :param kwargs: 其他参数（如槽位信息）
        :return: 格式化后的Prompt {"system": ..., "user": ...}
        """
        template = self.get_prompt(state)
        
        system_prompt = template["system"].strip()
        user_prompt = template["user"].format(
            query=query,
            context=context,
            **kwargs
        )
        
        return {
            "system": system_prompt,
            "user": user_prompt,
            "name": template["name"]
        }
    
    def get_template_names(self) -> list:
        """获取所有模板名称"""
        return [template["name"] for template in self.templates.values()]


# 全局Prompt管理器实例
prompt_manager = PromptManager()


# 测试函数
def test_prompt_manager():
    print("=== 测试Prompt管理器 ===")
    
    # 测试获取不同状态的Prompt
    states = [
        AgentState.MEDICAL_KNOWLEDGE,
        AgentState.USER_DECISION,
        AgentState.BUSINESS_CONVERSION,
    ]
    
    for state in states:
        prompt = prompt_manager.get_prompt(state)
        print(f"状态: {state.value}")
        print(f"模板名称: {prompt['name']}")
        print(f"System Prompt长度: {len(prompt['system'])} 字符")
        print(f"User Prompt模板: {prompt['user'][:50]}...")
        print()
    
    # 测试格式化Prompt
    formatted = prompt_manager.format_prompt(
        AgentState.BUSINESS_CONVERSION,
        "我想预约",
        name="张三",
        phone=None,
        service_type=None,
        time_slot=None
    )
    print("=== 格式化后的Prompt ===")
    print(f"Name: {formatted['name']}")
    print(f"System:\n{formatted['system'][:100]}...")
    print(f"User:\n{formatted['user']}")


if __name__ == "__main__":
    test_prompt_manager()