"""State reducers：不可变更新与 trace / 拷贝语义。"""
from __future__ import annotations

import pytest

from app.routing.policy_models import PolicyEvaluationResult
from app.state.agent_run_state import AgentRunState
from app.execution.schemas import ExecutionResult
from app.state.reducers import (
    apply_clarify_count_result,
    apply_execution_result,
    apply_generation_result,
    apply_retrieval_result,
    apply_routing_result,
    apply_understanding_result,
    clear_session_updates,
)
from app.understanding.schemas import UnderstandingResult


def _base_state() -> AgentRunState:
    return AgentRunState(user_id="u1", user_msg="hello")


def test_apply_understanding_result_new_reference_and_trace():
    s0 = _base_state()
    u = UnderstandingResult.normalize(
        "price_question",
        "多少钱",
        "Level 1",
        entities={"phone": "13800000000"},
        confidence=0.9,
        user_msg_for_entities="多少钱",
    )
    s1 = apply_understanding_result(s0, u)
    assert s1 is not s0
    assert s0.intent == ""
    assert s1.intent == "price_question"
    assert s1.trace["unified_understanding"]["intent"] == "price_question"
    assert s1.trace["unified_understanding"]["legacy_intent"] == s1.legacy_intent


def test_apply_understanding_result_entities_shallow_copy_independence():
    s0 = _base_state()
    u = UnderstandingResult.normalize(
        "appointment",
        "预约",
        "Level 1",
        entities={"name": "A"},
        confidence=0.8,
        user_msg_for_entities="预约",
    )
    s1 = apply_understanding_result(s0, u)
    u.entities["name"] = "B"
    assert s1.entities["name"] == "A"


def test_apply_routing_result_route_action_and_trace():
    s0 = _base_state()
    s0.trace["pre"] = 1
    rt = {"engine": "t", "rule_name": "r", "reason": "ok", "action": "clarify", "signals": {}}
    s1 = apply_routing_result(s0, action="clarify", route="clarify", routing_trace=rt)
    assert s1 is not s0
    assert s0.route == ""
    assert s1.route == "clarify"
    assert s1.action == "clarify"
    assert s1.trace["routing_policy"] == rt
    assert s1.trace["pre"] == 1


def test_apply_retrieval_result_contexts_copy():
    s0 = _base_state()
    ctx = ["a", "b"]
    tr = {"query": "q", "top_k": 3, "num_docs": 2, "retrieval_score": 0.5}
    s1 = apply_retrieval_result(
        s0,
        merged_retrieval_query="merged",
        contexts=ctx,
        retrieval_score=0.4,
        execution_retrieval_trace=tr,
    )
    assert s1 is not s0
    ctx.append("c")
    assert s1.contexts == ["a", "b"]
    assert s1.retrieval_score == pytest.approx(0.4)
    assert s1.merged_retrieval_query == "merged"
    assert s1.trace["execution_retrieval"]["query"] == "q"


def test_apply_generation_result_final_response_and_trace_merge():
    s0 = _base_state()
    s0.trace["routing_policy"] = {"x": 1}
    s1 = apply_generation_result(
        s0,
        final_response="ok",
        llm_generate_trace={"draft_len": 3},
        critic_trace={"passed_all": True, "items": []},
    )
    assert s1 is not s0
    assert s0.final_response is None
    assert s1.final_response == "ok"
    assert s1.trace["routing_policy"]["x"] == 1
    assert s1.trace["llm_generate"]["draft_len"] == 3
    assert s1.trace["critic"]["passed_all"] is True


def test_apply_generation_result_booking_trace():
    s0 = _base_state()
    s1 = apply_generation_result(s0, booking_trace={"status": "created"})
    assert s1.trace["booking"]["status"] == "created"


def test_apply_execution_result_merge_trace_and_session_updates():
    s0 = _base_state()
    s0.trace["a"] = 1
    er = ExecutionResult(
        response="hi",
        contexts=["x"],
        trace={"llm_generate": {"draft_len": 2}, "critic": {"passed_all": True}},
        meta={"session_ops": [{"op": "reset_clarify", "user_id": "u1"}]},
    )
    s1 = apply_execution_result(s0, er)
    assert s1 is not s0
    assert s1.contexts == ["x"]
    assert s1.trace["a"] == 1
    assert s1.trace["llm_generate"]["draft_len"] == 2
    assert s1.session_updates[0]["op"] == "reset_clarify"
    s2 = clear_session_updates(s1)
    assert s2.session_updates == []


def test_apply_clarify_count_result():
    s0 = _base_state()
    s1 = apply_clarify_count_result(s0, 2)
    assert s1 is not s0
    assert s0.clarify_count == 0
    assert s1.clarify_count == 2


def test_policy_evaluation_routing_roundtrip_trace_shape():
    """与 routing.build_routing_policy_trace 形状兼容（不 import routing 避免引擎加载）。"""
    s0 = _base_state()
    s0.risk_level = "Level 2"
    s0.retrieval_score = 0.1
    s0.clarify_count = 0
    pe = PolicyEvaluationResult(action="clarify", rule_name="t", reason="r")
    rt = {
        "engine": "policy_engine_yaml_v1",
        "rule_name": pe.rule_name,
        "reason": pe.reason,
        "action": pe.action,
        "signals": {
            "risk_level": "Level 2",
            "retrieval_score": 0.1,
            "clarify_count": 0,
        },
    }
    s1 = apply_routing_result(s0, action=pe.action, route=pe.action, routing_trace=rt)
    assert s1.action == "clarify"
