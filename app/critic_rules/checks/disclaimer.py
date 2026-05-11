from __future__ import annotations

from typing import Tuple

from app.critic_rules.checks.common import CheckItemResult
from app.critic_rules.constants import DEFAULT_DISCLAIMER_SUFFIX, DISCLAIMER_TERMS
from app.critic_rules.context import CriticContext


def check_high_risk_disclaimer(ctx: CriticContext, draft: str) -> Tuple[str, CheckItemResult]:
    cid = "high_risk_disclaimer"
    if ctx.risk_level not in ("Level 2", "Level 3"):
        return draft, CheckItemResult(cid, True, "none")
    if any(t in draft for t in DISCLAIMER_TERMS):
        return draft, CheckItemResult(cid, True, "none", "disclaimer_present")
    text = draft.rstrip() + DEFAULT_DISCLAIMER_SUFFIX
    return text, CheckItemResult(cid, False, "append", "missing_disclaimer_appended")
