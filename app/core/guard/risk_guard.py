from typing import Optional


RISK_KEYWORDS = [
    "保证治好",
    "包治",
    "确诊",
    "开药",
    "诊断书",
    "百分百",
]

COMPLAINT_KEYWORDS = [
    "投诉",
    "差评",
    "骂",
    "骗子",
    "维权",
]


def needs_handoff(user_text: str) -> bool:
    return any(word in user_text for word in COMPLAINT_KEYWORDS)


def risk_block_reply(user_text: str) -> Optional[str]:
    if any(word in user_text for word in RISK_KEYWORDS):
        return "医疗问题需要由医生面诊判断，我不能提供确诊、疗效承诺或处方建议。若您方便，我可以立即为您转人工客服进一步协助。"
    return None
