"""
评估指标（离线批量）：基于 golden 期望字段做轻量断言式打分。

后续可接人工标注或 LLM-as-judge，不改变本模块函数签名。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


def routing_accuracy(results: List[Dict[str, Any]]) -> float:
    """若有 ``expect.route`` / ``matched_rule`` 等字段可扩展；当前占位为通过率。"""
    if not results:
        return 0.0
    ok = sum(1 for r in results if not r.get("metric_errors"))
    return round(ok / len(results), 4)


def booking_success_rate(results: List[Dict[str, Any]]) -> float:
    """占位：可检测 trace 中 booking 成功片段。"""
    if not results:
        return 0.0
    hits = 0
    for r in results:
        traces = r.get("traces") or []
        for t in traces:
            snap = t.get("state_snapshot") or {}
            if snap.get("action") == "booking":
                hits += 1
                break
    return round(hits / len(results), 4)


def retrieval_precision_proxy(results: List[Dict[str, Any]]) -> float:
    """用 ``retrieval_score`` 与 contexts 数量作粗代理（非 IR 意义 precision）。"""
    if not results:
        return 0.0
    scores: List[float] = []
    for r in results:
        traces = r.get("traces") or []
        if not traces:
            continue
        snap = traces[-1].get("state_snapshot") or {}
        rs = float(snap.get("retrieval_score") or 0.0)
        nctx = int(snap.get("num_contexts") or 0)
        scores.append(min(1.0, rs + 0.1 * min(nctx, 3)))
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 4)


def score_replay_against_expect(
    replay: Dict[str, Any], case: Dict[str, Any]
) -> Dict[str, Any]:
    """对单条 replay 结果对照 ``case["expect"]`` 生成 ``metric_errors`` 列表。"""
    expect = case.get("expect") or {}
    errors: List[str] = []
    reply = (replay.get("reply") or "").strip()

    if expect.get("reply_not_empty") and not reply:
        errors.append("empty_reply")

    if expect.get("trace_has_understanding"):
        found = False
        for t in replay.get("traces") or []:
            for ev in t.get("events") or []:
                if not isinstance(ev, dict):
                    continue
                if ev.get("step") == "graph_step" and (ev.get("data") or {}).get(
                    "node"
                ) == "understanding":
                    found = True
                    break
                if ev.get("step") == "state_snapshot" and (ev.get("data") or {}).get(
                    "intent"
                ):
                    found = True
                    break
            if found:
                break
        if not found:
            errors.append("missing_understanding_trace")

    if expect.get("no_unqualified_cure_promise"):
        banned = ("包治", "保证治好", "百分百治好")
        if any(b in reply for b in banned):
            errors.append("unqualified_cure_promise")

    if expect.get("min_turns"):
        if replay.get("turn_count", 0) < int(expect["min_turns"]):
            errors.append("min_turns_not_met")

    out = dict(replay)
    out["metric_errors"] = errors
    return out


def run_golden_batch(*, cases_path: Path | None = None) -> Dict[str, Any]:
    """加载 golden_cases、逐条回放并打分，便于 CI 或本地对比 workflow 版本。"""
    from app.eval.replay_engine import load_golden_cases, replay_conversation

    data = load_golden_cases(cases_path)
    cases = data.get("cases", [])
    scored: List[Dict[str, Any]] = []
    for c in cases:
        rep = replay_conversation(c)
        scored.append(score_replay_against_expect(rep, c))
    return {
        "workflow_version_check": "compare app.workflows.dental.workflow.WORKFLOW_VERSION",
        "case_count": len(scored),
        "cases": scored,
        "routing_accuracy": routing_accuracy(scored),
        "booking_success_rate": booking_success_rate(scored),
        "retrieval_precision_proxy": retrieval_precision_proxy(scored),
    }
