"""
纯函数 state reducer：old state + result → new state。

禁止：副作用、IO、logging（由调用方负责观测）。
"""
from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any, Mapping, Optional

from app.state.agent_run_state import AgentRunState

if TYPE_CHECKING:
    from app.execution.schemas import ExecutionResult
from app.understanding.intent_bridge import v3_to_legacy_intent
from app.understanding.schemas import UnderstandingResult


def _clone_run_state(state: AgentRunState) -> AgentRunState:
    """浅拷贝容器 + 拷贝可变字段，避免 reducer 间共享引用。"""
    return replace(
        state,
        entities=dict(state.entities),
        contexts=list(state.contexts),
        trace=dict(state.trace),
        session_updates=list(state.session_updates),
    )


def apply_understanding_result(
    state: AgentRunState,
    result: UnderstandingResult,
) -> AgentRunState:
    legacy = v3_to_legacy_intent(result.intent)
    s = _clone_run_state(state)
    s.intent = result.intent
    s.rewritten_query = (result.rewritten_query or "").strip() or state.user_msg
    s.risk_level = result.risk_level
    s.legacy_intent = legacy
    s.entities = dict(result.entities)
    s.conversation_stage = result.conversation_stage
    s.understanding_confidence = result.confidence
    u_trace = {**result.to_trace_dict(), "legacy_intent": legacy}
    s.trace = {**s.trace, "unified_understanding": u_trace}
    return s


def apply_routing_result(
    state: AgentRunState,
    *,
    action: str,
    route: str,
    routing_trace: Mapping[str, Any],
) -> AgentRunState:
    s = _clone_run_state(state)
    s.action = action
    s.route = route
    s.trace = {**s.trace, "routing_policy": dict(routing_trace)}
    return s


def apply_clarify_count_result(state: AgentRunState, clarify_count: int) -> AgentRunState:
    s = _clone_run_state(state)
    s.clarify_count = int(clarify_count)
    return s


def apply_retrieval_result(
    state: AgentRunState,
    *,
    merged_retrieval_query: Optional[str] = None,
    contexts: Optional[list[str]] = None,
    retrieval_score: Optional[float] = None,
    execution_retrieval_trace: Optional[Mapping[str, Any]] = None,
) -> AgentRunState:
    s = _clone_run_state(state)
    if merged_retrieval_query is not None:
        s.merged_retrieval_query = merged_retrieval_query
    if contexts is not None:
        s.contexts = list(contexts)
    if retrieval_score is not None:
        s.retrieval_score = float(retrieval_score)
    if execution_retrieval_trace is not None:
        s.trace = {**s.trace, "execution_retrieval": dict(execution_retrieval_trace)}
    return s


def apply_generation_result(
    state: AgentRunState,
    *,
    final_response: Optional[str] = None,
    llm_generate_trace: Optional[Mapping[str, Any]] = None,
    critic_trace: Optional[Mapping[str, Any]] = None,
    booking_trace: Optional[Mapping[str, Any]] = None,
    action: Optional[str] = None,
    route: Optional[str] = None,
) -> AgentRunState:
    s = _clone_run_state(state)
    if final_response is not None:
        s.final_response = final_response
    if action is not None:
        s.action = action
    if route is not None:
        s.route = route
    new_trace = dict(s.trace)
    if llm_generate_trace is not None:
        new_trace["llm_generate"] = dict(llm_generate_trace)
    if critic_trace is not None:
        new_trace["critic"] = dict(critic_trace) if isinstance(critic_trace, Mapping) else critic_trace
    if booking_trace is not None:
        new_trace["booking"] = dict(booking_trace)
    s.trace = new_trace
    return s


def apply_execution_result(state: AgentRunState, result: "ExecutionResult") -> AgentRunState:
    """合并 ExecutionResult 的 trace/contexts/session_updates（纯函数）。"""
    from app.execution.schemas import ExecutionResult as ER

    if not isinstance(result, ER):
        raise TypeError("result must be ExecutionResult")
    s = _clone_run_state(state)
    s.trace = {**s.trace, **dict(result.trace)}
    s.contexts = list(result.contexts)
    ops = result.meta.get("session_ops")
    if ops is not None:
        s.session_updates = list(ops)
    return s


def clear_session_updates(state: AgentRunState) -> AgentRunState:
    s = _clone_run_state(state)
    s.session_updates = []
    return s


def merge_trace(state: AgentRunState, key: str, value: Any) -> AgentRunState:
    s = _clone_run_state(state)
    s.trace = {**s.trace, key: value}
    return s


def apply_workflow_early_exit(
    state: AgentRunState,
    *,
    response: str,
    trace_key: str,
    trace_payload: Mapping[str, Any],
) -> AgentRunState:
    """短路结束：设置 early_exit + final_response + trace 片段。"""
    s = _clone_run_state(state)
    s.early_exit = True
    s.final_response = response
    s.trace = {**s.trace, trace_key: dict(trace_payload)}
    return s
