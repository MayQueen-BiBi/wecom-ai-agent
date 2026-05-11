"""
生产链路冒烟：HTTP → entry → workflow；路由快照；批量无崩溃。

说明：批量循环次数在 CI 中保持适中；本地可将 ``SMOKE_LOAD_ITERATIONS`` 调至 100。
"""
from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.api.entry import invoke_request
from app.api.protocol import AgentRequest
from app.main import app

SMOKE_LOAD_ITERATIONS = int(os.environ.get("SMOKE_LOAD_ITERATIONS", "12"))


def test_health_ok() -> None:
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_dev_chat_webhook_style_entry_not_empty() -> None:
    """等价于浏览器调 ``/dev/chat``：经统一 entry，响应非空。"""
    client = TestClient(app)
    r = client.get(
        "/dev/chat",
        params={"msg": "种植牙多少钱", "user_id": "smoke_webhook_1"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("reply") is not None
    assert len(str(body.get("reply"))) > 0
    assert body.get("trace_id")


def test_routing_snapshot_allowed_actions() -> None:
    """路由/动作落在策略枚举常见值之一（大小写不敏感）。"""
    res = invoke_request(
        AgentRequest(user_id="smoke_route_1", text="洗牙多少钱", channel="smoke")
    )
    assert res.success is True
    snap = (res.extras or {}).get("snapshot") or {}
    route = str(snap.get("route") or snap.get("action") or "").lower()
    allowed = {
        "generate",
        "booking",
        "clarify",
        "degrade",
        "serve_cache",
        "handoff_static",
    }
    assert route in allowed or route == "", f"unexpected route/action: {route!r}"


def test_load_no_crash() -> None:
    """并发式压力由 entry 信号量约束；此处仅验证连续调用不崩溃。"""
    for i in range(SMOKE_LOAD_ITERATIONS):
        res = invoke_request(
            AgentRequest(
                user_id=f"smoke_load_{i}",
                text="你好",
                channel="smoke",
                metadata={"i": i},
            )
        )
        assert res.reply is not None
