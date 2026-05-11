"""
L5 可观测性：trace 含关键阶段；graph_step 携带 state diff 摘要。

回放依赖 ``extras.trace`` 中 ``events``（含 ``graph_step`` / ``state_snapshot``）。
"""
from __future__ import annotations

import pytest

from app.api.entry import invoke_request
from app.api.protocol import AgentRequest

from tests.acceptance.helpers import graph_step_nodes, has_graph_step_diff_metadata, trace_blob


@pytest.fixture
def uid() -> str:
    return "acc_l5_trace"


def test_l5_trace_contains_pipeline_stages(uid: str) -> None:
    res = invoke_request(
        AgentRequest(
            user_id=f"{uid}_1",
            text="种植牙多少钱",
            channel="acceptance_l5",
            metadata={},
        )
    )
    blob = trace_blob(res)
    nodes = graph_step_nodes(res)
    assert "understanding" in nodes or "understanding" in blob
    assert "routing" in nodes or "routing" in blob
    assert "execution" in nodes or "execution" in blob


def test_l5_graph_step_includes_diff_metadata(uid: str) -> None:
    res = invoke_request(
        AgentRequest(
            user_id=f"{uid}_2",
            text="洗牙多少钱",
            channel="acceptance_l5",
            metadata={},
        )
    )
    assert has_graph_step_diff_metadata(res), "graph_step should carry changed_keys (state diff)"
