from __future__ import annotations

import re
from typing import Tuple

from app.critic_rules.checks.common import CheckItemResult, degrade_safe_reply
from app.critic_rules.constants import (
    ABSOLUTE_PROMISE_PATTERN,
    RETRIEVAL_SCORE_STRONG_ANSWER_FORBID_MAX,
    STRONG_OUTCOME_PATTERN,
)
from app.critic_rules.context import CriticContext


def check_promises_outside_retrieval(ctx: CriticContext, draft: str) -> Tuple[str, CheckItemResult]:
    """无检索或弱检索时禁止「超证据」绝对承诺。"""
    cid = "no_medical_promise_beyond_retrieval"
    weak = (len(ctx.contexts) == 0) or (
        ctx.retrieval_score < RETRIEVAL_SCORE_STRONG_ANSWER_FORBID_MAX
    )
    if not weak:
        return draft, CheckItemResult(cid, True, "none")
    if re.search(ABSOLUTE_PROMISE_PATTERN, draft):
        return (
            degrade_safe_reply(),
            CheckItemResult(cid, False, "replace", "absolute_promise_without_evidence"),
        )
    return draft, CheckItemResult(cid, True, "none")


def check_low_retrieval_forbid_strong_answer(ctx: CriticContext, draft: str) -> Tuple[str, CheckItemResult]:
    """retrieval 证据弱时禁止强医疗结论表述。"""
    cid = "low_retrieval_no_strong_answer"
    if ctx.retrieval_score >= RETRIEVAL_SCORE_STRONG_ANSWER_FORBID_MAX:
        return draft, CheckItemResult(cid, True, "none")
    if re.search(STRONG_OUTCOME_PATTERN, draft) or re.search(ABSOLUTE_PROMISE_PATTERN, draft):
        return (
            degrade_safe_reply(),
            CheckItemResult(
                cid,
                False,
                "replace",
                "strong_medical_claim_under_weak_retrieval",
            ),
        )
    return draft, CheckItemResult(cid, True, "none")
