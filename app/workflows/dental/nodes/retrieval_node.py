"""检索阶段。"""
from __future__ import annotations

import time

from app.execution.adapters.retrieval_adapter import execute_retrieval
from app.state.agent_run_state import AgentRunState
from app.workflows.dental.context import get_dental_graph_context


async def run(state: AgentRunState) -> AgentRunState:
    ctx = get_dental_graph_context()
    step_start = time.time()
    new_state = execute_retrieval(state, ctx.sm)
    ctx.tracker.add_step(
        "Execution.Retrieval",
        {"score": new_state.retrieval_score, "n": len(new_state.contexts)},
        (time.time() - step_start) * 1000,
    )
    return new_state
