"""薄封装：检索子过程 → reducer 更新 state（逻辑仍在 execution_layer）。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.execution.dental_execution_layer import (
    compute_merged_retrieval_query,
    run_execution_retrieval,
)
from app.state.reducers import apply_retrieval_result

if TYPE_CHECKING:
    from app.core.runtime.state_machine import StateMachine
    from app.state.agent_run_state import AgentRunState


def execute_retrieval(state: "AgentRunState", sm: "StateMachine") -> "AgentRunState":
    merged = compute_merged_retrieval_query(state, sm)
    contexts, score, trace = run_execution_retrieval(merged, sm)
    return apply_retrieval_result(
        state,
        merged_retrieval_query=merged,
        contexts=contexts,
        retrieval_score=score,
        execution_retrieval_trace=trace,
    )
