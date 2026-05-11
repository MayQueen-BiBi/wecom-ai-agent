"""Policy engine YAML + critic checklist（无 LLM）。"""
from __future__ import annotations

from app.critic_rules import CriticContext, run_checklist
from app.routing import PolicyRoute, evaluate_routing_action
from app.state.agent_run_state import AgentRunState


def _state(**kwargs) -> AgentRunState:
    s = AgentRunState(user_id="u", user_msg="test")
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s


def test_engine_default_generate():
    r = evaluate_routing_action(_state(retrieval_score=0.8, risk_level="Level 2", clarify_count=0))
    assert r.action == PolicyRoute.GENERATE.value
    assert r.rule_name == "default"


def test_engine_clarify_low_retrieval():
    r = evaluate_routing_action(_state(retrieval_score=0.1, risk_level="Level 2", clarify_count=0))
    assert r.action == PolicyRoute.CLARIFY.value
    assert r.rule_name == "low_retrieval_clarify"


def test_engine_degrade_after_clarify_cap():
    r = evaluate_routing_action(_state(retrieval_score=0.1, risk_level="Level 2", clarify_count=2))
    assert r.action == PolicyRoute.DEGRADE.value
    assert r.rule_name == "clarify_rounds_exhausted_low_retrieval"


def test_engine_level3_weak_evidence_clarify_before_retrieval():
    r = evaluate_routing_action(_state(retrieval_score=0.2, risk_level="Level 3", clarify_count=0))
    assert r.action == PolicyRoute.CLARIFY.value
    assert r.rule_name == "high_risk_weak_evidence_clarify"


def test_critic_disclaimer_appends_for_level3():
    ctx = CriticContext(
        intent="medical_consulting",
        risk_level="Level 3",
        retrieval_score=0.8,
        contexts=("doc",),
    )
    r = run_checklist(ctx, "种植牙材料有区别。")
    assert "面诊" in r.final_text or "医生" in r.final_text


def test_critic_low_retrieval_blocks_strong_claim():
    ctx = CriticContext(
        intent="medical_consulting",
        risk_level="Level 1",
        retrieval_score=0.1,
        contexts=(),
    )
    r = run_checklist(ctx, "我们保证一定能治愈。")
    assert r.passed_all is False
    assert "面诊" in r.final_text or "诊疗" in r.final_text
