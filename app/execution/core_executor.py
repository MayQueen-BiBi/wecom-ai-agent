"""
纯执行器：state + action → ExecutionResult（不修改 state、不访问 session_store）。
对话上下文写入 StateMachine；session / cache / metrics 由 workflow 处理。
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List

from app.core.guard.retrieval_guard import clarification_prompt, degrade_response
from app.core.llm.client import call_llm
from app.core.runtime.state_machine import AgentState
from app.core.tools.base import call_tool
from app.understanding.prompt_templates import prompt_manager
from app.config.settings import QWEN_API_KEY
from app.critic_rules import CriticContext, run_checklist
from app.execution.schemas import ExecutionResult
from app.routing.policy_models import PolicyRoute
from app.understanding.extraction import post_process_answer

if TYPE_CHECKING:
    from app.core.runtime.state_machine import StateMachine
    from app.state.agent_run_state import AgentRunState

logger = logging.getLogger(__name__)


def _dispatch(
    state: "AgentRunState",
    action: str,
    sm: "StateMachine",
    *,
    cache_query: str,
    prev_sm_state: AgentState,
    current_sm_state: AgentState,
    legacy_intent_for_metrics: str,
) -> ExecutionResult:
    _ = prev_sm_state
    if action == PolicyRoute.CLARIFY.value:
        msg = clarification_prompt(state.merged_retrieval_query)
        sm.get_context().add_conversation_turn(state.user_msg, msg)
        return ExecutionResult(
            response=msg,
            contexts=list(state.contexts),
            trace={},
            meta={
                "session_ops": [{"op": "increment_clarify", "user_id": state.user_id}],
            },
        )
    if action == PolicyRoute.DEGRADE.value:
        msg = degrade_response()
        sm.get_context().add_conversation_turn(state.user_msg, msg)
        return ExecutionResult(
            response=msg,
            contexts=list(state.contexts),
            trace={},
            meta={
                "session_ops": [{"op": "reset_clarify", "user_id": state.user_id}],
            },
        )
    if action == PolicyRoute.GENERATE.value:
        return _execute_generate(
            state,
            sm,
            cache_query=cache_query,
            current_sm_state=current_sm_state,
            legacy_intent_for_metrics=legacy_intent_for_metrics,
        )
    if action == PolicyRoute.BOOKING.value:
        return _execute_booking(state, sm)

    logger.warning("unknown action=%s, degrade", action)
    msg = degrade_response()
    sm.get_context().add_conversation_turn(state.user_msg, msg)
    return ExecutionResult(
        response=msg,
        contexts=list(state.contexts),
        trace={"execution_unknown_action": action},
        meta={
            "session_ops": [{"op": "reset_clarify", "user_id": state.user_id}],
        },
    )


def _execute_booking(state: "AgentRunState", sm: "StateMachine") -> ExecutionResult:
    slots = sm.get_context().slots
    result = call_tool(
        "create_appointment",
        {
            "name": slots["name"],
            "phone": slots["phone"],
            "time": slots["time_slot"],
            "service": slots["service_type"],
        },
    )
    sm.get_context().add_conversation_turn(state.user_msg, result)
    sm.reset()
    return ExecutionResult(
        response=result,
        contexts=list(state.contexts),
        trace={"booking": {"status": "created"}},
        meta={
            "session_ops": [
                {"op": "reset_clarify", "user_id": state.user_id},
            ],
        },
    )


def _execute_generate(
    state: "AgentRunState",
    sm: "StateMachine",
    *,
    cache_query: str,
    current_sm_state: AgentState,
    legacy_intent_for_metrics: str,
) -> ExecutionResult:
    session_ops: List[Dict[str, Any]] = [
        {"op": "reset_clarify", "user_id": state.user_id},
    ]
    conversation_history = sm.get_context().get_conversation_history()
    context_text = "\n".join(f"[{i+1}] {doc}" for i, doc in enumerate(state.contexts))
    prompt = prompt_manager.format_prompt(
        state=current_sm_state,
        query=state.user_msg,
        context=context_text,
        history=conversation_history,
        **sm.get_context().slots,
    )
    draft = call_llm(prompt["system"], prompt["user"])
    trace: Dict[str, Any] = {
        "llm_generate": {
            "prompt_name": prompt.get("name"),
            "draft_len": len(draft),
            "has_key": bool(QWEN_API_KEY),
        },
    }
    critic_ctx = CriticContext.from_run_state(state)
    critic_result = run_checklist(critic_ctx, draft)
    final_text = critic_result.final_text
    trace["critic"] = critic_result.to_trace_dict()

    if current_sm_state == AgentState.BUSINESS_CONVERSION:
        slots = sm.get_context().slots
        if (
            slots.get("name")
            and slots.get("phone")
            and slots.get("service_type")
            and slots.get("time_slot")
        ):
            ber = _execute_booking(state, sm)
            trace = {**trace, **ber.trace}
            session_ops.extend(ber.meta.get("session_ops", []))
            return ExecutionResult(
                response=ber.response,
                contexts=list(state.contexts),
                trace=trace,
                meta={
                    "session_ops": session_ops,
                },
            )

    final_text = post_process_answer(final_text, state.contexts)
    sm.get_context().add_conversation_turn(state.user_msg, final_text)
    return ExecutionResult(
        response=final_text,
        contexts=list(state.contexts),
        trace=trace,
        meta={
            "session_ops": session_ops,
            "cache_write": {
                "key": cache_query,
                "value": final_text,
                "metadata": {
                    "intent_v3": state.intent,
                    "legacy": legacy_intent_for_metrics,
                    "state": current_sm_state.value,
                },
            },
            "metrics": {"cache_hit": False},
        },
    )


async def execute(
    state: "AgentRunState",
    action: str,
    *,
    sm: "StateMachine",
    cache_query: str,
    prev_sm_state: AgentState,
    current_sm_state: AgentState,
    legacy_intent_for_metrics: str,
) -> ExecutionResult:
    return _dispatch(
        state,
        action,
        sm,
        cache_query=cache_query,
        prev_sm_state=prev_sm_state,
        current_sm_state=current_sm_state,
        legacy_intent_for_metrics=legacy_intent_for_metrics,
    )


def execute_sync(
    state: "AgentRunState",
    action: str,
    *,
    sm: "StateMachine",
    cache_query: str,
    prev_sm_state: AgentState,
    current_sm_state: AgentState,
    legacy_intent_for_metrics: str,
) -> ExecutionResult:
    return _dispatch(
        state,
        action,
        sm,
        cache_query=cache_query,
        prev_sm_state=prev_sm_state,
        current_sm_state=current_sm_state,
        legacy_intent_for_metrics=legacy_intent_for_metrics,
    )
