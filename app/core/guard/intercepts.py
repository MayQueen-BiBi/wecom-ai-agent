from typing import Optional

from app.core.guard.risk_guard import needs_handoff, risk_block_reply
from app.core.runtime.state_machine import StateMachine
from app.understanding.extraction import EXIT_KEYWORDS


def is_exit_intent(user_msg: str) -> bool:
    return any(k in user_msg for k in EXIT_KEYWORDS)


def handle_static_intercepts(
    user_id: str, user_msg: str, sm: StateMachine
) -> Optional[str]:
    """无需 LLM 的静态链路：风控、转人工、退出重置。"""
    if risk_block_reply(user_msg):
        return "对话涉及敏感信息，请咨询线下门诊。"

    if needs_handoff(user_msg):
        return "正在为您转接专业医护人员..."

    if is_exit_intent(user_msg):
        sm.reset()
        return "好的，期待下次为您服务。"

    return None
