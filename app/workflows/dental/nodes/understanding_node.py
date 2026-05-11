"""understanding：统一语义 + 状态机意图 + 语义缓存短路。"""
from __future__ import annotations

import time

from app.observability.metrics import update_metrics
from app.state.agent_run_state import AgentRunState
from app.state.reducers import apply_understanding_result, apply_workflow_early_exit
from app.state.session_store import session_store
from app.core.cache.cache import semantic_cache
from app.understanding.unified_understanding import understand
from app.workflows.dental.context import get_dental_graph_context


async def run(state: AgentRunState) -> AgentRunState:
    ctx = get_dental_graph_context()
    step_start = time.time()
    last_u = ctx.sm.get_context().get_last_user_message()
    u = understand(state.user_msg, last_u)
    state = apply_understanding_result(state, u)
    ctx.sm.process_intent(state.legacy_intent, u.confidence)
    ctx.current_sm_state = ctx.sm.get_current_state()
    ctx.tracker.add_step(
        "Unified Understanding",
        state.trace.get("unified_understanding", {}),
        (time.time() - step_start) * 1000,
    )

    ctx.cache_query = f"[v3:{state.intent}] {state.rewritten_query}"
    cached = semantic_cache.get(ctx.cache_query)
    if not cached:
        return state

    update_metrics(state.legacy_intent, ctx.prev_sm_state, ctx.current_sm_state, cache_hit=True)
    session_store.reset_clarify(ctx.user_id)
    ctx.app_trace.add("cache_hit", {"key": ctx.cache_query[:60]})
    ctx.sm.get_context().add_conversation_turn(ctx.user_msg, cached[0])
    ctx.tracker.set_final_answer(cached[0])
    ctx.last_reply = cached[0]
    return apply_workflow_early_exit(
        state,
        response=cached[0],
        trace_key="cache_hit",
        trace_payload={"key": ctx.cache_query[:60]},
    )
