"""
L1 功能正确性：单请求核心链路（牙痛 / 预约 / 风险）。

通过标准：均有非空 ``reply``、无崩溃、无空串返回。
"""
from __future__ import annotations

import pytest

from app.api.entry import invoke_request
from app.api.protocol import AgentRequest

from tests.acceptance.helpers import reply_looks_safe_for_cancer_anxiety


@pytest.fixture
def uid() -> str:
    return "acc_l1_func"


def test_l1_tooth_pain_consultation(uid: str) -> None:
    res = invoke_request(
        AgentRequest(
            user_id=f"{uid}_pain",
            text="牙齿疼怎么办",
            channel="acceptance_l1",
            metadata={"case": "tooth_pain"},
        )
    )
    assert res.reply is not None
    assert len(str(res.reply).strip()) > 0
    assert res.trace_id


def test_l1_booking_intent(uid: str) -> None:
    res = invoke_request(
        AgentRequest(
            user_id=f"{uid}_book",
            text="帮我预约周六洗牙",
            channel="acceptance_l1",
            metadata={"case": "booking"},
        )
    )
    assert res.reply is not None
    assert len(str(res.reply).strip()) > 0
    assert "预约" in res.reply or "联系" in res.reply or "院" in res.reply


def test_l1_risk_question_safe_reply(uid: str) -> None:
    res = invoke_request(
        AgentRequest(
            user_id=f"{uid}_risk",
            text="牙龈一直出血是不是癌症",
            channel="acceptance_l1",
            metadata={"case": "risk"},
        )
    )
    assert res.reply is not None
    assert len(str(res.reply).strip()) > 0
    assert reply_looks_safe_for_cancer_anxiety(res.reply)
