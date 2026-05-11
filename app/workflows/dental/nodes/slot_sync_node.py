"""槽位同步到 StateMachine。"""
from __future__ import annotations

from app.state.agent_run_state import AgentRunState
from app.workflows.dental.context import get_dental_graph_context


async def run(state: AgentRunState) -> AgentRunState:
    ctx = get_dental_graph_context()
    ctx.sm.sync_slots(dict(state.entities))
    ctx.app_trace.add("slots", {"from_understanding": state.entities})
    return state
