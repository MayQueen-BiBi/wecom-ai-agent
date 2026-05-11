"""Graph 运行期上下文（节点通过 ContextVar 读取，不写入 AgentRunState）。"""
from __future__ import annotations

import contextvars
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.core.runtime.state_machine import AgentState, StateMachine
    from app.observability.flow_tracker import FlowTracker
    from app.observability.trace import RequestTrace


@dataclass
class DentalGraphContext:
    user_id: str
    user_msg: str
    sm: "StateMachine"
    tracker: "FlowTracker"
    app_trace: "RequestTrace"
    t0: float
    prev_sm_state: "AgentState"
    current_sm_state: Optional["AgentState"] = None
    cache_query: str = ""
    last_reply: str = ""


_ctx: contextvars.ContextVar[Optional[DentalGraphContext]] = contextvars.ContextVar(
    "dental_graph_ctx", default=None
)


def get_dental_graph_context() -> DentalGraphContext:
    c = _ctx.get()
    if c is None:
        raise RuntimeError("DentalGraphContext is not set for this task")
    return c


def set_dental_graph_context(ctx: DentalGraphContext):
    return _ctx.set(ctx)


def reset_dental_graph_context(token) -> None:
    _ctx.reset(token)
