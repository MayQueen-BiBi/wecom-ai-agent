import json
import requests
from typing import Optional, Dict
from app.agent.rag_enhanced import rag_search
from app.agent.risk_guard import needs_handoff, risk_block_reply
from app.agent.session import get_session, reset_appointment
from app.agent.tools import call_tool
from app.config.settings import QWEN_API_KEY

QWEN_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

# 退出意图关键词
EXIT_KEYWORDS = ["算了", "不预约了", "取消", "退出", "结束"]

# 服务类型列表
SERVICE_TYPES = ["种植牙", "正畸", "洗牙", "补牙", "拔牙", "牙痛检查"]

# LLM 越权检测关键词
FORBIDDEN_PHRASES = ["预约成功", "已为您预约", "挂号成功", "预约已完成"]


def _is_appointment_intent(user_msg: str) -> bool:
    """检测预约意图（FSM决策）"""
    keywords = ["预约", "挂号", "到院", "面诊", "看牙", "安排时间"]
    return any(k in user_msg for k in keywords)


def _is_exit_intent(user_msg: str) -> bool:
    """检测退出意图（FSM决策）"""
    return any(k in user_msg for k in EXIT_KEYWORDS)


def _extract_phone(user_msg: str) -> Optional[str]:
    """提取手机号（工具函数）"""
    digits = "".join(ch for ch in user_msg if ch.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        return digits
    return None


def _extract_time(user_msg: str) -> Optional[str]:
    """提取时间（工具函数）"""
    if ":" in user_msg:
        for token in user_msg.split():
            if ":" in token:
                return token.strip("，。,.")
    for token in ["今天", "明天", "后天", "上午", "下午", "晚上"]:
        if token in user_msg:
            return token
    return None


def _extract_service(user_msg: str) -> Optional[str]:
    """提取服务类型（工具函数）"""
    for service in SERVICE_TYPES:
        if service in user_msg:
            return service
    return None


def _validate_llm_response(response: str, session_state: str) -> str:
    """验证LLM输出，防止越权（输出验证层）"""
    if session_state != "appointment_completed":
        for phrase in FORBIDDEN_PHRASES:
            if phrase in response:
                # LLM越权，返回安全提示
                return "我已记录您的需求，正在为您处理..."
    
    return response


def _llm_fallback(user_msg: str) -> str:
    """LLM兜底：仅用于自然语言生成（最小权限原则）"""
    if not QWEN_API_KEY:
        return "我可以先回答基础问题，并协助您预约。请问需要预约还是咨询？"

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
                    你是牙科医院客服助理。
                    ⚠️ 严格规则：
                    1. 你只能回答问题，**不能执行任何预约操作**
                    2. 如果用户要求预约，请引导他们提供姓名和电话
                    3. **绝对不要说"预约成功"或类似的话**
                    4. 最终预约确认由系统完成，你无权确认
                    5. 禁止诊断和疗效承诺
                    """
                },
                {
                    "role": "user",
                    "content": user_msg
                }
            ]
        },
        "parameters": {
            "result_format": "message"
        }
    }

    try:
        resp = requests.post(QWEN_URL, headers=headers, json=payload, timeout=5)

        if resp.status_code != 200:
            print("LLM HTTP ERROR:", resp.status_code, resp.text)
            return "暂时无法智能回复，请问您是想预约还是咨询？"

        result = resp.json()
        print("LLM RAW RESULT:", result)

        if "code" in result:
            print("LLM API ERROR:", result)
            return "我可以帮您预约洗牙、补牙或解答常见问题，请问需要什么服务？"

        return result["output"]["choices"][0]["message"]["content"]

    except Exception as e:
        print("LLM EXCEPTION:", e)
        return "网络有点忙，我可以先帮您预约或解答基础问题。"


def _handle_appointment_flow(session, user_msg: str) -> str:
    """处理预约流程（FSM决策核心）"""
    appointment = session.appointment

    # 增量提取信息（职责分离：信息提取）
    if not appointment["name"]:
        name_candidate = user_msg.strip()
        if len(name_candidate) <= 8 and "@" not in name_candidate and _extract_phone(name_candidate) is None:
            appointment["name"] = name_candidate

    phone = _extract_phone(user_msg)
    if phone:
        appointment["phone"] = phone

    service = _extract_service(user_msg)
    if service and not appointment["service"]:
        appointment["service"] = service
        if service not in session.tags:
            session.tags.append(service)

    time_val = _extract_time(user_msg)
    if time_val:
        appointment["time"] = time_val

    # FSM决策：检查是否需要继续收集
    if not appointment["name"]:
        return "好的，我来帮您预约。请先告诉我您的称呼（姓名）。"
    if not appointment["phone"]:
        return "收到。请再提供您的11位手机号，方便确认预约信息。"
    if not appointment["service"]:
        return "请问您想预约哪项服务？例如：种植牙、正畸、洗牙。"
    if not appointment["time"]:
        slots = call_tool("get_slots", {})
        return f"可预约时段有：{', '.join(slots)}。请回复您方便的时间。"

    # FSM决策：所有信息完整，执行预约
    call_tool(
        "create_appointment",
        {
            "name": appointment["name"],
            "phone": appointment["phone"],
            "time": appointment["time"],
            "service": appointment["service"],
        },
    )
    session.transition_to("appointment_completed")
    reset_appointment(session)
    return "已为您登记预约，我们会尽快与您确认到院安排。若您需要，我也可以继续解答项目相关问题。"


def run_agent(user_id: str, user_msg: str):
    """主入口：严格遵循 FSM优先 + LLM兜底 原则"""
    session = get_session(user_id)

    # 优先级1：风险拦截（职责分离）
    blocked = risk_block_reply(user_msg)
    if blocked:
        return blocked

    # 优先级2：人工转接（FSM决策）
    if needs_handoff(user_msg):
        session.handoff = True
        session.transition_to("handoff_pending")
        return "已为您转接人工客服，请稍候。为便于快速处理，您也可以补充您的姓名和联系电话。"

    # 优先级3：退出意图（FSM决策）
    if _is_exit_intent(user_msg):
        reset_appointment(session)
        return "好的，如有需要随时找我预约。"

    # 优先级4：预约流程（FSM决策核心）
    if _is_appointment_intent(user_msg) or session.state == "appointment_collecting":
        session.transition_to("appointment_collecting")
        return _handle_appointment_flow(session, user_msg)

    # 优先级5：RAG检索（增强版）
    rag_answer, evaluation = rag_search(user_msg)
    if rag_answer:
        # 记录评估结果（用于监控和优化）
        print(f"RAG评估结果 - 相关性: {evaluation['relevance']:.2f}, 准确性: {evaluation['accuracy']:.2f}, 有用性: {evaluation['usefulness']:.2f}")
        return rag_answer + " 如需我帮您直接安排面诊预约，也可以告诉我。"

    # 优先级6：LLM兜底（最小权限原则）
    llm_response = _llm_fallback(user_msg)
    validated_response = _validate_llm_response(llm_response, session.state)
    return validated_response
