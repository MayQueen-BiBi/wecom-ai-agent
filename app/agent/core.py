import json
import requests
from typing import Optional
from app.agent.faq import faq_search
from app.agent.risk_guard import needs_handoff, risk_block_reply
from app.agent.session import get_session, reset_appointment
from app.agent.tools import call_tool
from app.config.settings import QWEN_API_KEY


QWEN_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"


def _is_appointment_intent(user_msg: str) -> bool:
    keywords = ["预约", "挂号", "到院", "面诊", "看牙", "安排时间"]
    return any(k in user_msg for k in keywords)


def _extract_phone(user_msg: str) -> Optional[str]:
    digits = "".join(ch for ch in user_msg if ch.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        return digits
    return None


def _extract_time(user_msg: str) -> Optional[str]:
    if ":" in user_msg:
        for token in user_msg.split():
            if ":" in token:
                return token.strip("，。,.")
    for token in ["今天", "明天", "后天", "上午", "下午", "晚上"]:
        if token in user_msg:
            return token
    return None


def _llm_fallback(user_msg: str) -> str:
    if not QWEN_API_KEY:
        return "我可以先回答基础问题，并协助您预约。若您愿意，我现在就帮您登记姓名、电话和到院时间。"

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
                    "content": "你是牙科医院客服。禁止给出诊断、疗效承诺、绝对价格。回答要简洁，并尽量引导用户预约到院检查。"
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

    resp = requests.post(QWEN_URL, headers=headers, json=payload, timeout=20)
    result = resp.json()
    return result["output"]["choices"][0]["message"]["content"]


def run_agent(user_id: str, user_msg: str):
    session = get_session(user_id)

    if needs_handoff(user_msg):
        session["handoff"] = True
        session["state"] = "handoff_pending"
        return "已为您转接人工客服，请稍候。为便于快速处理，您也可以补充您的姓名和联系电话。"

    blocked = risk_block_reply(user_msg)
    if blocked:
        return blocked

    if _is_appointment_intent(user_msg) or session["state"] == "appointment_collecting":
        session["state"] = "appointment_collecting"
        appointment = session["appointment"]

        if appointment["name"] is None and len(user_msg.strip()) <= 8 and "@" not in user_msg and _extract_phone(user_msg) is None:
            appointment["name"] = user_msg.strip()

        phone = _extract_phone(user_msg)
        if phone:
            appointment["phone"] = phone

        for service in ["种植牙", "正畸", "洗牙", "补牙", "拔牙", "牙痛检查"]:
            if service in user_msg:
                appointment["service"] = service
                if service not in session["tags"]:
                    session["tags"].append(service)
                break

        time_val = _extract_time(user_msg)
        if time_val:
            appointment["time"] = time_val

        if not appointment["name"]:
            return "好的，我来帮您预约。请先告诉我您的称呼（姓名）。"
        if not appointment["phone"]:
            return "收到。请再提供您的11位手机号，方便确认预约信息。"
        if not appointment["service"]:
            return "请问您想预约哪项服务？例如：种植牙、正畸、洗牙。"
        if not appointment["time"]:
            slots = call_tool("get_slots", {})
            return f"可预约时段有：{', '.join(slots)}。请回复您方便的时间。"

        call_tool(
            "create_appointment",
            {
                "name": appointment["name"],
                "phone": appointment["phone"],
                "time": appointment["time"],
                "service": appointment["service"],
            },
        )
        reset_appointment(session)
        session["state"] = "consulting"
        return "已为您登记预约，我们会尽快与您确认到院安排。若您需要，我也可以继续解答项目相关问题。"

    faq_answer = faq_search(user_msg)
    if faq_answer:
        return faq_answer + " 如需我帮您直接安排面诊预约，也可以告诉我。"

    fallback = _llm_fallback(user_msg)
    if isinstance(fallback, list):
        return json.dumps(fallback, ensure_ascii=False)
    return fallback