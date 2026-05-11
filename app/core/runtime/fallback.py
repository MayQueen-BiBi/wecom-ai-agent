"""
统一降级文案：高风险或无法理解时的安全回复。

接入 workflow 出口，避免在高风险状态下输出不可控生成内容。
"""
from __future__ import annotations

from app.state.agent_run_state import AgentRunState


def is_high_risk(state: AgentRunState) -> bool:
    """
    临床/急诊类风险（Level 3）走固定降级，不依赖自由生成。
    Level 1 为商业敏感，仍走正常策略；可按产品再收紧。
    """
    rl = (state.risk_level or "").strip()
    return rl == "Level 3"


def fallback_response(state: AgentRunState) -> str:
    """固定话术，不读取用户原文细节（避免二次暴露）。"""
    _ = state
    return "我暂时无法理解您的问题，请换一种说法"


def maybe_fallback_reply(state: AgentRunState, reply: str) -> str:
    """若命中高风险，用降级文案替换模型输出。"""
    if is_high_risk(state):
        return fallback_response(state)
    return reply
