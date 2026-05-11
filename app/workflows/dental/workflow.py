"""
Dental V3：Graph Runtime 编排（`run_graph` + `DENTAL_GRAPH`）。
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Tuple, Optional

from app.core.runtime.fallback import maybe_fallback_reply
from app.observability.flow_tracker import FlowTracker
from app.observability.trace import RequestTrace
from app.observability.trace_graph import build_graph_step_observer
from app.state.agent_run_state import AgentRunState
from app.core.runtime.state_machine import StateMachine
from app.workflows.dental.context import (
    DentalGraphContext,
    reset_dental_graph_context,
    set_dental_graph_context,
)
from app.workflows.dental.graph import DENTAL_GRAPH
from app.workflows.runtime.graph import run_graph

logger = logging.getLogger(__name__)

WORKFLOW_VERSION = "v1.0"

user_state_machines: Dict[str, StateMachine] = {}


def _get_sm(user_id: str) -> StateMachine:
    if user_id not in user_state_machines:
        user_state_machines[user_id] = StateMachine()
    return user_state_machines[user_id]


async def _run_dental_graph_async(
    user_id: str,
    user_msg: str,
    sm: StateMachine,
    tracker: FlowTracker,
    app_trace: RequestTrace,
    t0: float,
    *,
    initial_state: Optional[AgentRunState] = None,
) -> Tuple[AgentRunState, DentalGraphContext]:
    state = initial_state or AgentRunState(user_id=user_id, user_msg=user_msg)
    ctx = DentalGraphContext(
        user_id=state.user_id,
        user_msg=state.user_msg,
        sm=sm,
        tracker=tracker,
        app_trace=app_trace,
        t0=t0,
        prev_sm_state=sm.get_current_state(),
    )
    app_trace.add("workflow", {"version": WORKFLOW_VERSION, "graph": "dental_v3"})
    token = set_dental_graph_context(ctx)
    try:
        state = await run_graph(
            DENTAL_GRAPH,
            "intercept",
            state,
            on_after_node=build_graph_step_observer(app_trace),
        )
    finally:
        reset_dental_graph_context(token)
    return state, ctx


async def run_dental_turn_async(
    state: AgentRunState,
    *,
    trace_id: str | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    单次牙科 Graph 回合（可 await）。返回 ``(reply, trace_dict)``，``trace_dict`` 含 ``trace_id``。
    """
    tracker = FlowTracker(state.user_id, state.user_msg)
    app_trace = RequestTrace(trace_id=trace_id)
    sm = _get_sm(state.user_id)
    t0 = time.perf_counter()

    try:
        state, ctx = await _run_dental_graph_async(
            state.user_id,
            state.user_msg,
            sm,
            tracker,
            app_trace,
            t0,
            initial_state=state,
        )

        if state.early_exit:
            reply = (state.final_response or ctx.last_reply or "").strip()
            reply = maybe_fallback_reply(state, reply)
            tracker.log_summary()
            app_trace.add("done", {"latency_ms": round((time.perf_counter() - t0) * 1000, 2)})
            app_trace.add("state_snapshot", state.to_trace_dict())
            return reply, app_trace.to_dict()

        reply = ctx.last_reply or ""
        reply = maybe_fallback_reply(state, reply)
        tracker.set_final_answer(reply)
        app_trace.add(
            "done",
            {
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                "response_preview": reply[:120],
            },
        )
        app_trace.add("state_snapshot", state.to_trace_dict())
        logger.info("trace_summary=%s", app_trace.to_dict())

    except Exception as e:
        logger.exception("run_agent_v3 error: %s", e)
        tracker.set_error(str(e))
        tracker.log_summary()
        app_trace.add("error", {"message": str(e)})
        return "抱歉，处理您的请求时出现错误，请稍后重试。", app_trace.to_dict()

    tracker.log_summary()
    return reply, app_trace.to_dict()


def run_agent_v3(user_id: str, user_msg: str) -> str:
    text, _trace = run_agent_v3_with_trace(user_id, user_msg)
    return text


def run_agent_v3_with_trace(user_id: str, user_msg: str) -> Tuple[str, Dict[str, Any]]:
    return asyncio.run(
        run_dental_turn_async(AgentRunState(user_id=user_id, user_msg=user_msg))
    )
