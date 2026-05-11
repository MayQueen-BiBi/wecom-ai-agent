"""clarify 计数从 session 同步到 state。"""
from __future__ import annotations

from app.state.agent_run_state import AgentRunState
from app.state.reducers import apply_clarify_count_result
from app.state.session_store import session_store
from app.workflows.dental.context import get_dental_graph_context


async def run(state: AgentRunState) -> AgentRunState:
    ctx = get_dental_graph_context()
    cc = int(session_store.snapshot(ctx.user_id).get("clarify_count", 0))
    return apply_clarify_count_result(state, cc)
