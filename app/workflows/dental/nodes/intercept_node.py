"""intercept：静态拦截。"""
from __future__ import annotations

import time

from app.core.guard.intercepts import handle_static_intercepts
from app.state.agent_run_state import AgentRunState
from app.state.reducers import apply_workflow_early_exit
from app.workflows.dental.context import get_dental_graph_context


async def run(state: AgentRunState) -> AgentRunState:
    ctx = get_dental_graph_context()
    step_start = time.time()
    intercept = handle_static_intercepts(ctx.user_id, ctx.user_msg, ctx.sm)
    if not intercept:
        return state
    ctx.app_trace.add("static_intercept", {"response_preview": intercept[:80]})
    ctx.tracker.add_step("静态拦截", {}, (time.time() - step_start) * 1000)
    ctx.sm.get_context().add_conversation_turn(ctx.user_msg, intercept)
    ctx.tracker.set_final_answer(intercept)
    ctx.last_reply = intercept
    return apply_workflow_early_exit(
        state,
        response=intercept,
        trace_key="static_intercept",
        trace_payload={"response_preview": intercept[:80]},
    )
