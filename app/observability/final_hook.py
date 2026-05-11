"""
生产可观测：入口层统一埋点（结构化日志，便于检索与回放）。

与 ``RequestTrace.trace_id`` 对齐；不写入 PII 全量，仅预览长度。
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from app.api.protocol import AgentRequest, AgentResponse

logger = logging.getLogger("app.observability.final_hook")


def generate_trace_id() -> str:
    return str(uuid.uuid4())


def _snapshot_route(state_blob: Dict[str, Any]) -> Optional[str]:
    snap = state_blob.get("snapshot") if isinstance(state_blob, dict) else None
    if isinstance(snap, dict):
        return snap.get("route") or snap.get("action")
    return None


def log_request_complete(
    *,
    trace_id: str,
    request: AgentRequest,
    response: AgentResponse,
    latency_ms: float,
    state_blob: Dict[str, Any],
) -> None:
    """记录单条请求的输入摘要、路由/动作、成功标记、延迟与回复预览。"""
    routing = _snapshot_route(state_blob)
    trace = state_blob.get("trace") if isinstance(state_blob, dict) else {}
    ev_steps = []
    if isinstance(trace, dict):
        for ev in (trace.get("events") or [])[-12:]:
            if isinstance(ev, dict):
                ev_steps.append(ev.get("step"))

    logger.info(
        "agent_request_complete trace_id=%s channel=%s user_id=%s success=%s "
        "latency_ms=%.2f routing=%s ev_tail=%s in_preview=%r out_preview=%r",
        trace_id,
        request.channel,
        request.user_id,
        response.success,
        latency_ms,
        routing,
        ev_steps,
        (request.text or "")[:240],
        (response.reply or "")[:240],
        extra={
            "trace_id": trace_id,
            "input_len": len(request.text or ""),
            "output_len": len(response.reply or ""),
            "routing": routing,
            "execution_trace_tail": ev_steps,
        },
    )
