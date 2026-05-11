"""
Checklist 编排：顺序执行，可审计 trace。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple

from app.critic_rules.checks import (
    check_high_risk_disclaimer,
    check_intent_alignment,
    check_low_retrieval_forbid_strong_answer,
    check_promises_outside_retrieval,
)
from app.critic_rules.checks.common import CheckItemResult
from app.critic_rules.context import CriticContext

CheckFn = Callable[[CriticContext, str], Tuple[str, CheckItemResult]]


@dataclass
class CriticChecklistResult:
    passed_all: bool
    final_text: str
    items: List[CheckItemResult] = field(default_factory=list)

    def to_trace_dict(self) -> Dict[str, Any]:
        return {
            "engine": "checklist",
            "passed_all": self.passed_all,
            "items": [
                {
                    "id": i.check_id,
                    "passed": i.passed,
                    "action": i.action,
                    "detail": i.detail,
                }
                for i in self.items
            ],
        }


DEFAULT_CHECKS: Tuple[CheckFn, ...] = (
    check_intent_alignment,
    check_promises_outside_retrieval,
    check_low_retrieval_forbid_strong_answer,
    check_high_risk_disclaimer,
)


def run_checklist(ctx: CriticContext, draft: str) -> CriticChecklistResult:
    text = draft
    items: List[CheckItemResult] = []
    for fn in DEFAULT_CHECKS:
        text, item = fn(ctx, text)
        items.append(item)
    passed_all = all(i.passed for i in items)
    return CriticChecklistResult(passed_all=passed_all, final_text=text, items=items)
