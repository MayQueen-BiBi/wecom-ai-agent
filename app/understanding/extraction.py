import hashlib
from typing import Any, Dict, Optional

EXIT_KEYWORDS = ["算了", "不预约了", "取消", "退出", "结束"]

SERVICE_TYPES = ["种植牙", "正畸", "洗牙", "补牙", "拔牙", "牙痛检查"]


def extract_phone(user_msg: str) -> Optional[str]:
    digits = "".join(ch for ch in user_msg if ch.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        return digits
    return None


def extract_service(user_msg: str) -> Optional[str]:
    for service in SERVICE_TYPES:
        if service in user_msg:
            return service
    return None


def extract_slots(user_msg: str) -> Dict[str, Any]:
    slots: Dict[str, Any] = {}

    phone = extract_phone(user_msg)
    if phone:
        slots["phone"] = phone

    service = extract_service(user_msg)
    if service:
        slots["service_type"] = service

    reserved_phrases = [
        "帮我预约",
        "预约",
        "挂号",
        "我想预约",
        "安排时间",
        "我叫",
        "我是",
        "我的名字是",
    ]
    is_reserved = any(phrase in user_msg for phrase in reserved_phrases)
    if (
        len(user_msg.strip()) <= 8
        and "@" not in user_msg
        and not phone
        and not is_reserved
    ):
        slots["name"] = user_msg.strip()

    return slots


def generate_cache_key(intent: str, query: str) -> str:
    content = f"{intent}:{query[:100]}"
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def post_process_answer(answer: str, contexts: list) -> str:
    if not answer:
        return "暂时无法回答您的问题。"

    answer = answer.strip()

    if not contexts:
        answer += "\n\n建议您到院咨询专业医生获取更详细的信息。"

    return answer
