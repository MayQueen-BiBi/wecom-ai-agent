"""
图执行链路的结构化 trace（understanding → routing → retrieval → execution → critic 等）。

事件写入 ``state.trace["trace_graph"]``；可与 ``RequestTrace`` 并行。
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional


def trace_event(state: Any, event_name: str, payload: Any) -> None:
    """在 ``state.trace`` 下追加一条流水线事件（需 ``state`` 带 ``trace: dict``）。"""
    if state is None:
        return
    tr = getattr(state, "trace", None)
    if not isinstance(tr, dict):
        return
    body: dict[str, Any]
    if isinstance(payload, dict):
        body = dict(payload)
    else:
        body = {"value": payload}
    events = tr.setdefault("trace_graph", [])
    events.append(
        {
            "event": event_name,
            "ts": time.time(),
            "payload": body,
        }
    )


def build_graph_step_observer(
    app_trace: Optional[Any] = None,
) -> Callable[[str, Any, Any], None]:
    """
    供 ``run_graph(..., on_after_node=...)`` 使用：记录事件 + state diff 摘要。

    * 完整 diff 挂在 ``state_after.trace["state_diffs"]``。
    * 若提供 ``app_trace``，追加轻量 ``graph_step`` 片段（仅变更字段名，防膨胀）。
    """
    from app.observability.state_diff import diff_state

    def on_after_node(node_id: str, state_before: Any, state_after: Any) -> None:
        trace_event(state_after, node_id, {"node": node_id, "phase": node_id})
        structured = diff_state(state_before, state_after)
        if hasattr(state_after, "trace") and isinstance(state_after.trace, dict):
            state_after.trace.setdefault("state_diffs", []).append(
                {"after_node": node_id, "structured_diff": structured}
            )
        if app_trace is not None:
            changed = structured.get("changed") if isinstance(structured, dict) else None
            keys = list(changed.keys())[:40] if isinstance(changed, dict) else []
            app_trace.add(
                "graph_step",
                {"node": node_id, "changed_keys": keys, "changed_count": len(keys)},
            )

    return on_after_node
