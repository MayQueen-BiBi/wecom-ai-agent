"""
Golden case 回放：驱动真实 workflow，收集 trace 与最终回复。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.workflows.dental.workflow import run_agent_v3_with_trace

_DEFAULT_CASES = Path(__file__).resolve().parent / "golden_cases.json"


def load_golden_cases(path: Path | None = None) -> Dict[str, Any]:
    p = path or _DEFAULT_CASES
    data = json.loads(p.read_text(encoding="utf-8"))
    return data


def replay_conversation(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行单个 case 的全部 turns，返回最后一条回复与每轮 trace。

    ``case`` 结构见 ``golden_cases.json``（``id`` / ``turns`` / ``expect``）。
    """
    turns: List[Dict[str, str]] = case.get("turns") or []
    traces: List[Dict[str, Any]] = []
    last_reply = ""
    for turn in turns:
        uid = str(turn.get("user_id", "eval_default"))
        msg = str(turn.get("user_msg", ""))
        reply, trace = run_agent_v3_with_trace(uid, msg)
        last_reply = reply
        traces.append(trace)
    return {
        "case_id": case.get("id"),
        "description": case.get("description"),
        "reply": last_reply,
        "traces": traces,
        "turn_count": len(turns),
    }


def replay_case(case_id: str, *, cases_path: Path | None = None) -> Dict[str, Any]:
    data = load_golden_cases(cases_path)
    for c in data.get("cases", []):
        if c.get("id") == case_id:
            return replay_conversation(c)
    raise KeyError(f"unknown golden case id: {case_id}")


def replay_all_cases(*, cases_path: Path | None = None) -> List[Dict[str, Any]]:
    data = load_golden_cases(cases_path)
    return [replay_conversation(c) for c in data.get("cases", [])]
