"""Dental YAML 路由引擎（薄封装 `decide_routing`）。"""
from __future__ import annotations

from app.routing import decide_routing
from app.routing.interfaces import RoutingDecision
from app.state.agent_run_state import AgentRunState


class DentalYamlRoutingEngine:
    def evaluate(self, state: AgentRunState) -> RoutingDecision:
        return decide_routing(state)


dental_routing_engine = DentalYamlRoutingEngine()
