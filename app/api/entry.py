"""
统一 API 入口：``AgentRequest`` → Graph workflow → ``AgentResponse``。

含：并发信号量、全链路超时、最终可观测钩子。
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict

from app.api.protocol import AgentRequest, AgentResponse, WorkflowGraphResult
from app.core.runtime.limits import MAX_CONCURRENT_REQUESTS, MAX_WORKFLOW_TIME_S
from app.observability.final_hook import generate_trace_id, log_request_complete
from app.state.agent_run_state import AgentRunState
from app.workflows.dental.workflow import WORKFLOW_VERSION, run_dental_turn_async

logger = logging.getLogger(__name__)

_request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


def build_state(req: AgentRequest) -> AgentRunState:
    """由协议构造本轮 ``AgentRunState``（含渠道与元数据旁路）。"""
    st = AgentRunState(user_id=req.user_id, user_msg=req.text)
    if req.channel:
        st.trace["channel"] = req.channel
    if req.metadata:
        st.trace["request_metadata"] = dict(req.metadata)
    return st


def _last_snapshot_from_trace(trace_dict: Dict[str, Any]) -> Dict[str, Any]:
    snap: Dict[str, Any] = {}
    for ev in trace_dict.get("events") or []:
        if isinstance(ev, dict) and ev.get("step") == "state_snapshot":
            snap = ev.get("data") or {}
    return snap


async def run_workflow_graph(
    state: AgentRunState,
    *,
    trace_id: str | None = None,
) -> WorkflowGraphResult:
    """执行牙科 Graph；返回结构化结果（供组装 :class:`AgentResponse`）。"""
    reply, trace_dict = await run_dental_turn_async(state, trace_id=trace_id)
    tid = str(trace_dict.get("trace_id") or trace_id or "")
    snapshot = _last_snapshot_from_trace(trace_dict)
    return WorkflowGraphResult(
        final_response=reply,
        trace_id=tid,
        state=snapshot,
        trace=trace_dict,
    )


async def handle_request(req: AgentRequest) -> AgentResponse:
    if not str(req.user_id or "").strip():
        tid = generate_trace_id()
        res = AgentResponse(
            reply="无效请求",
            trace_id=tid,
            success=False,
            extras={"reason": "empty_user_id"},
        )
        log_request_complete(
            trace_id=tid,
            request=req,
            response=res,
            latency_ms=0.0,
            state_blob={},
        )
        return res
    if not str(req.text or "").strip():
        tid = generate_trace_id()
        res = AgentResponse(
            reply="无效请求",
            trace_id=tid,
            success=False,
            extras={"reason": "empty_text"},
        )
        log_request_complete(
            trace_id=tid,
            request=req,
            response=res,
            latency_ms=0.0,
            state_blob={},
        )
        return res

    trace_id = generate_trace_id()
    t0 = time.perf_counter()
    async with _request_semaphore:
        try:
            async with asyncio.timeout(MAX_WORKFLOW_TIME_S):
                state = build_state(req)
                result = await run_workflow_graph(state, trace_id=trace_id)
        except TimeoutError:
            latency_ms = (time.perf_counter() - t0) * 1000
            res = AgentResponse(
                reply="系统繁忙，请稍后再试",
                trace_id=trace_id,
                success=False,
                extras={"error": "timeout"},
            )
            log_request_complete(
                trace_id=trace_id,
                request=req,
                response=res,
                latency_ms=latency_ms,
                state_blob={"snapshot": {}, "trace": {"events": []}},
            )
            logger.warning("handle_request timeout trace_id=%s", trace_id)
            return res
        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.exception("handle_request error trace_id=%s", trace_id)
            res = AgentResponse(
                reply="系统繁忙，请稍后再试",
                trace_id=trace_id,
                success=False,
                extras={"error": str(e)},
            )
            log_request_complete(
                trace_id=trace_id,
                request=req,
                response=res,
                latency_ms=latency_ms,
                state_blob={"snapshot": {}, "trace": {"events": []}},
            )
            return res

    latency_ms = (time.perf_counter() - t0) * 1000
    extras: Dict[str, Any] = {
        "snapshot": result.state,
        "trace": result.trace,
        "workflow_version": WORKFLOW_VERSION,
    }
    res = AgentResponse(
        reply=result.final_response,
        trace_id=result.trace_id or trace_id,
        success=True,
        extras=extras,
    )
    log_request_complete(
        trace_id=res.trace_id,
        request=req,
        response=res,
        latency_ms=latency_ms,
        state_blob=extras,
    )
    return res


def invoke_request(req: AgentRequest) -> AgentResponse:
    """同步调用（测试 / 脚本）：内部 ``asyncio.run``。"""
    return asyncio.run(handle_request(req))


async def handle_request_with_trace(req: AgentRequest) -> tuple[AgentResponse, Dict[str, Any]]:
    res = await handle_request(req)
    trace = (res.extras or {}).get("trace") or {}
    return res, trace


def invoke_request_with_trace(req: AgentRequest) -> tuple[AgentResponse, Dict[str, Any]]:
    return asyncio.run(handle_request_with_trace(req))
