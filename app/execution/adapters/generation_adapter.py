"""薄封装：执行分发（生成/澄清/降级/预约）→ 返回 (reply, new_state)。"""
from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

from app.core.runtime.state_machine import AgentState
from app.execution.dental_execution_layer import execution_dispatch

if TYPE_CHECKING:
    from app.core.runtime.state_machine import StateMachine
    from app.state.agent_run_state import AgentRunState


def execute_generation_dispatch(
    state: "AgentRunState",
    sm: "StateMachine",
    *,
    cache_query: str,
    prev_sm_state: AgentState,
    current_sm_state: AgentState,
    legacy_intent_for_metrics: str,
) -> Tuple[str, "AgentRunState"]:
    return execution_dispatch(
        state,
        sm,
        cache_query=cache_query,
        prev_sm_state=prev_sm_state,
        current_sm_state=current_sm_state,
        legacy_intent_for_metrics=legacy_intent_for_metrics,
    )
