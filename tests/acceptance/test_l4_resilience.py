"""
L4 异常恢复：空输入、非法路径、超时降级。

系统不得裸崩溃；入口层须返回可展示文案。
"""
from __future__ import annotations

import asyncio

import pytest

from app.api.entry import handle_request, invoke_request
from app.api.protocol import AgentRequest


def test_l4_empty_text_returns_fallback() -> None:
    res = asyncio.run(
        handle_request(
            AgentRequest(
                user_id="acc_l4_empty", text="", channel="acceptance_l4", metadata={}
            )
        )
    )
    assert res.reply is not None
    assert len(res.reply) > 0
    assert res.success is False


def test_l4_whitespace_user_id_invalid() -> None:
    res = asyncio.run(
        handle_request(
            AgentRequest(user_id="   ", text="你好", channel="acceptance_l4", metadata={})
        )
    )
    assert res.reply is not None
    assert res.success is False


def test_l4_workflow_timeout_entry_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.api.entry as entry

    async def _slow(*_a, **_kw):
        await asyncio.sleep(2.0)
        from app.api.protocol import WorkflowGraphResult

        return WorkflowGraphResult(
            final_response="should not return",
            trace_id="slow",
            state={},
            trace={},
        )

    monkeypatch.setattr(entry, "run_workflow_graph", _slow)
    monkeypatch.setattr(entry, "MAX_WORKFLOW_TIME_S", 0.08, raising=False)

    res = asyncio.run(
        handle_request(
            AgentRequest(
                user_id="acc_l4_timeout",
                text="你好",
                channel="acceptance_l4",
                metadata={},
            )
        )
    )
    assert res.success is False
    assert "稍后再试" in res.reply or "繁忙" in res.reply


def test_l4_invoke_never_raises_on_valid_contract() -> None:
    """合法 ``AgentRequest`` 不应因协议构造失败。"""
    res = invoke_request(
        AgentRequest(user_id="acc_l4_ok", text="谢谢", channel="acceptance_l4", metadata={})
    )
    assert res.reply is not None
