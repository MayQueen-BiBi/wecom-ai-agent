"""
Routing Policy V1：仅产出 RoutingDecision；state 写入由 workflow + reducer 完成。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from app.routing.interfaces import RoutingDecision
from app.routing.policy_engine import PolicyEngine
from app.routing.policy_models import PolicyEvaluationResult, PolicyRoute
from app.state.reducers import apply_routing_result

if TYPE_CHECKING:
    from app.state.agent_run_state import AgentRunState

_engine: PolicyEngine | None = None


def _get_engine() -> PolicyEngine:
    global _engine
    if _engine is None:
        _engine = PolicyEngine.from_default_yaml()
    return _engine


def evaluate_routing_action(state: "AgentRunState") -> PolicyEvaluationResult:
    """State → Policy → Action（单出口）。"""
    return _get_engine().evaluate(state)


def build_routing_policy_trace(
    state: "AgentRunState", result: PolicyEvaluationResult
) -> Dict[str, Any]:
    """与 `apply_routing_result` 对齐的 trace 载荷（纯数据，无副作用）。"""
    return {
        "engine": "policy_engine_yaml_v1",
        "rule_name": result.rule_name,
        "reason": result.reason,
        "action": result.action,
        "signals": {
            "risk_level": (state.risk_level or "").strip() or "Level 2",
            "retrieval_score": float(state.retrieval_score or 0.0),
            "clarify_count": int(state.clarify_count or 0),
        },
    }


def decide_routing(state: "AgentRunState") -> RoutingDecision:
    """纯函数：不修改 state。"""
    if state.early_exit or state.final_response:
        act = (state.action or PolicyRoute.GENERATE.value)
        rte = (state.route or PolicyRoute.GENERATE.value)
        return RoutingDecision(
            action=act,
            route=rte,
            trace={
                "engine": "policy_engine_yaml_v1",
                "rule_name": "skipped",
                "reason": "early_exit_or_final_response",
                "action": act,
                "signals": {
                    "risk_level": (state.risk_level or "").strip() or "Level 2",
                    "retrieval_score": float(state.retrieval_score or 0.0),
                    "clarify_count": int(state.clarify_count or 0),
                },
            },
        )
    result = evaluate_routing_action(state)
    rt = build_routing_policy_trace(state, result)
    return RoutingDecision(action=result.action, route=result.action, trace=rt)


def apply_routing_policy(state: "AgentRunState") -> "AgentRunState":
    """兼容：decide + reducer。"""
    d = decide_routing(state)
    return apply_routing_result(
        state,
        action=d.action,
        route=d.route,
        routing_trace=d.trace,
    )


def cache_hit_routing_decision(state: "AgentRunState") -> RoutingDecision:
    """语义缓存命中时的路由决策（纯数据）。"""
    act = PolicyRoute.SERVE_CACHE.value
    return RoutingDecision(
        action=act,
        route=act,
        trace={
            "engine": "policy_engine_yaml_v1",
            "rule_name": "semantic_cache_hit",
            "reason": "semantic_cache_hit",
            "action": act,
            "signals": {
                "risk_level": (state.risk_level or "").strip() or "Level 2",
                "retrieval_score": float(state.retrieval_score or 0.0),
                "clarify_count": int(state.clarify_count or 0),
            },
        },
    )


def handoff_static_routing_decision(state: "AgentRunState") -> RoutingDecision:
    act = PolicyRoute.HANDOFF_STATIC.value
    return RoutingDecision(
        action=act,
        route=act,
        trace={
            "engine": "policy_engine_yaml_v1",
            "rule_name": "handoff_static",
            "reason": "static_handoff_route",
            "action": act,
            "signals": {
                "risk_level": (state.risk_level or "").strip() or "Level 2",
                "retrieval_score": float(state.retrieval_score or 0.0),
                "clarify_count": int(state.clarify_count or 0),
            },
        },
    )


def set_cache_route(state: "AgentRunState") -> None:
    """遗留 API：仍原地写 state；新代码请用 cache_hit_routing_decision + reducer。"""
    d = cache_hit_routing_decision(state)
    state.route = d.route
    state.action = d.action
    state.trace["routing_policy"] = d.trace


def set_handoff_static_route(state: "AgentRunState") -> None:
    """遗留 API：仍原地写 state；新代码请用 handoff_static_routing_decision + reducer。"""
    d = handoff_static_routing_decision(state)
    state.route = d.route
    state.action = d.action
    state.trace["routing_policy"] = d.trace
