"""单次请求的链路快照（可对接 Langfuse 等）。"""
import time
import uuid
from typing import Any, Dict, List, Optional


class RequestTrace:
    def __init__(self, trace_id: Optional[str] = None) -> None:
        self.trace_id = trace_id or str(uuid.uuid4())
        self.events: List[Dict[str, Any]] = []
        self.t0 = time.perf_counter()

    def add(self, step: str, payload: Optional[Dict[str, Any]] = None) -> None:
        self.events.append(
            {
                "step": step,
                "t_ms": round((time.perf_counter() - self.t0) * 1000, 2),
                "data": payload or {},
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "events": self.events,
            "total_ms": round((time.perf_counter() - self.t0) * 1000, 2),
        }
