from dataclasses import dataclass


@dataclass
class CheckItemResult:
    check_id: str
    passed: bool
    action: str  # "none" | "append" | "replace"
    detail: str = ""


def degrade_safe_reply() -> str:
    return (
        "医疗问题需要医生面诊判断，我无法代替诊疗。"
        "建议您预约到院检查，或转人工客服协助。"
    )
