"""Routing 层协议（边界冻结；实现可逐步对齐）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol, runtime_checkable

from app.state.agent_run_state import AgentRunState


@dataclass(frozen=True)
class RoutingDecision:
    """纯路由决策：不含 state 写入；trace 与 `apply_routing_result` 对齐。"""

    action: str
    route: str
    trace: Dict[str, Any]


@runtime_checkable
class RoutingEngine(Protocol):
    def evaluate(self, state: AgentRunState) -> RoutingDecision:
        """纯 state → 决策；须确定性、无 LLM。"""
        ...
