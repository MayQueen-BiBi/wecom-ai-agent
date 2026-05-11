"""execution：core_executor + reducer + session/cache/metrics 收尾。"""
from __future__ import annotations

import time

from app.execution.dental_execution_layer import complete_generation_dispatch
from app.execution.core_executor import execute
from app.state.agent_run_state import AgentRunState
from app.workflows.dental.context import get_dental_graph_context


async def run(state: AgentRunState) -> AgentRunState:
    ctx = get_dental_graph_context()
    step_start = time.time()
    cur = ctx.current_sm_state or ctx.prev_sm_state
    er = await execute(
        state,
        state.action,
        sm=ctx.sm,
        cache_query=ctx.cache_query,
        prev_sm_state=ctx.prev_sm_state,
        current_sm_state=cur,
        legacy_intent_for_metrics=state.legacy_intent,
    )
    reply, new_state = complete_generation_dispatch(
        state,
        er,
        user_id=state.user_id,
        prev_sm_state=ctx.prev_sm_state,
        current_sm_state=cur,
        legacy_intent_for_metrics=state.legacy_intent,
    )
    ctx.last_reply = reply
    ctx.tracker.add_step(
        "Execution.Dispatch",
        {"action": new_state.action},
        (time.time() - step_start) * 1000,
    )
    return new_state
