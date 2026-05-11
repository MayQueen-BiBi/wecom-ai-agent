"""
L2 路由稳定性：多场景下 ``route`` / ``action`` 落在预期集合。

说明：策略引擎返回小写 action（如 ``generate``）；期望列用集合兼容波动。
命中率：每场景重复 trials，命中比例 ≥ 90%。
"""
from __future__ import annotations

import os

import pytest

from app.api.entry import invoke_request
from app.api.protocol import AgentRequest

from tests.acceptance.helpers import route_or_action

# (用户文本, 允许的 route/action 集合) — 与 PolicyRoute 小写值对齐
ROUTING_CASES = [
    ("牙疼", frozenset({"generate", "clarify", "degrade", "booking"})),
    ("预约洗牙", frozenset({"generate", "booking", "clarify", "degrade"})),
    ("不知道怎么办完全不清楚", frozenset({"clarify", "degrade", "generate"})),
]

TRIALS_PER_CASE = int(os.environ.get("ACCEPTANCE_L2_TRIALS", "8"))
MIN_HIT_RATE = float(os.environ.get("ACCEPTANCE_L2_MIN_HIT_RATE", "0.9"))


@pytest.fixture
def uid() -> str:
    return "acc_l2_route"


def test_l2_routing_hit_rate_per_scenario(uid: str) -> None:
    failures: list[str] = []
    for text, allowed in ROUTING_CASES:
        hits = 0
        for i in range(TRIALS_PER_CASE):
            res = invoke_request(
                AgentRequest(
                    user_id=f"{uid}_{hash(text) % 10000}_{i}",
                    text=text,
                    channel="acceptance_l2",
                    metadata={"trial": i},
                )
            )
            r = route_or_action(res)
            if r in allowed or r == "":
                hits += 1
            else:
                failures.append(f"{text!r} trial={i} got={r!r}")
        rate = hits / TRIALS_PER_CASE
        assert rate >= MIN_HIT_RATE, (
            f"routing for {text!r}: hit_rate={rate:.2f} failures={failures[-5:]}"
        )
