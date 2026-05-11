"""routing：纯决策 + reducer 写入 state。"""
from __future__ import annotations

from app.state.agent_run_state import AgentRunState
from app.state.reducers import apply_routing_result
from app.workflows.dental.context import get_dental_graph_context
from app.workflows.dental.routing_engine import dental_routing_engine


async def run(state: AgentRunState) -> AgentRunState:
    ctx = get_dental_graph_context()
    decision = dental_routing_engine.evaluate(state)
    new_state = apply_routing_result(
        state,
        action=decision.action,
        route=decision.route,
        routing_trace=decision.trace,
    )
    ctx.app_trace.add("routing", {"route": new_state.route, "action": new_state.action})
    return new_state
