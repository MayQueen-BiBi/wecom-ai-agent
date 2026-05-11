"""
Unified Understanding Node：系统唯一的自然语言 → 结构化语义入口。
"""
from __future__ import annotations

from app.state.agent_run_state import AgentRunState
from app.understanding.intent_bridge import v3_to_legacy_intent
from app.understanding.llm_node import run_unified_semantic_understanding
from app.understanding.schemas import UnderstandingResult


def understand(user_msg: str, last_user_message: str | None = None) -> UnderstandingResult:
    """返回结构化 UnderstandingResult；不做路由、检索或回复生成。"""
    return run_unified_semantic_understanding(user_msg, last_user_message)


def apply_understanding_result_to_state(state: AgentRunState, u: UnderstandingResult) -> None:
    """将 UnderstandingResult 写入 AgentRunState（不含 StateMachine / 执行层）。"""
    state.intent = u.intent
    state.rewritten_query = (u.rewritten_query or "").strip() or state.user_msg
    state.risk_level = u.risk_level
    state.legacy_intent = v3_to_legacy_intent(u.intent)
    state.entities = dict(u.entities)
    state.conversation_stage = u.conversation_stage
    state.understanding_confidence = u.confidence
    state.trace["unified_understanding"] = {
        **u.to_trace_dict(),
        "legacy_intent": state.legacy_intent,
    }
