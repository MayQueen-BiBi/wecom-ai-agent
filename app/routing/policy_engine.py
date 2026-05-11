"""
Policy Engine V1：加载 YAML 规则，按序对 state 做首条命中求值。
仅使用 risk_level / retrieval_score / clarify_count。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, List

import yaml
from pydantic import ValidationError

from app.routing.policy_models import (
    PolicyEvaluationResult,
    PolicyFile,
    PolicyRow,
    PolicyRoute,
)

if TYPE_CHECKING:
    from app.state.agent_run_state import AgentRunState

logger = logging.getLogger(__name__)

POLICY_VERSION = "2026-05"

_POLICIES_DIR = Path(__file__).resolve().parent / "policies"
_POLICY_FILES = (
    "risk_rules.yaml",
    "retrieval_rules.yaml",
    "clarify_rules.yaml",
)


def _load_policy_file(path: Path) -> List[PolicyRow]:
    if not path.is_file():
        logger.warning("policy file missing: %s", path)
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        return []
    try:
        pf = PolicyFile.model_validate(raw)
    except ValidationError as e:
        logger.error("invalid policy file %s: %s", path, e)
        return []
    for row in pf.rules:
        if row.condition.constraint_count() == 0:
            logger.error("policy row %r in %s has empty condition", row.name, path)
            raise ValueError(f"Policy row {row.name!r} must have at least one condition field")
    return list(pf.rules)


class PolicyEngine:
    """稳定入口：evaluate(state) → action。"""

    def __init__(self, rules: List[PolicyRow]) -> None:
        self._rules = rules

    @classmethod
    def from_default_yaml(cls) -> "PolicyEngine":
        rows: List[PolicyRow] = []
        for name in _POLICY_FILES:
            rows.extend(_load_policy_file(_POLICIES_DIR / name))
        return cls(rows)

    def evaluate(self, state: "AgentRunState") -> PolicyEvaluationResult:
        risk = (state.risk_level or "").strip() or "Level 2"
        rs = float(state.retrieval_score or 0.0)
        cc = int(state.clarify_count or 0)

        for row in self._rules:
            if row.condition.matches(risk, rs, cc):
                return PolicyEvaluationResult(
                    action=row.action,
                    rule_name=row.name,
                    reason=f"matched_rule:{row.name}",
                )

        return PolicyEvaluationResult(
            action=PolicyRoute.GENERATE.value,
            rule_name="default",
            reason="no_rule_matched",
        )
