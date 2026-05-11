"""Routing Policy V1：Pydantic 模型（State → Policy → Action）。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PolicyRoute(str, Enum):
    """与 Execution 分发的 action 标签一致。"""

    SERVE_CACHE = "serve_cache"
    CLARIFY = "clarify"
    DEGRADE = "degrade"
    GENERATE = "generate"
    BOOKING = "booking"
    HANDOFF_STATIC = "handoff_static"


class PolicyCondition(BaseModel):
    """
    V1 仅支持：risk_level、retrieval_score、clarify_count。
    未设置的字段不参与匹配；至少须有一项约束（加载时校验）。
    """

    model_config = ConfigDict(extra="forbid")

    risk_level_eq: Optional[str] = None

    retrieval_score_lt: Optional[float] = None
    retrieval_score_lte: Optional[float] = None
    retrieval_score_gt: Optional[float] = None
    retrieval_score_gte: Optional[float] = None

    clarify_count_lt: Optional[int] = None
    clarify_count_lte: Optional[int] = None
    clarify_count_gt: Optional[int] = None
    clarify_count_gte: Optional[int] = None
    clarify_count_eq: Optional[int] = None

    def constraint_count(self) -> int:
        d = self.model_dump(exclude_none=True)
        return len(d)

    def matches(self, risk_level: str, retrieval_score: float, clarify_count: int) -> bool:
        if self.constraint_count() == 0:
            return False

        if self.risk_level_eq is not None and risk_level != self.risk_level_eq:
            return False
        rs = retrieval_score
        if self.retrieval_score_lt is not None and not (rs < self.retrieval_score_lt):
            return False
        if self.retrieval_score_lte is not None and not (rs <= self.retrieval_score_lte):
            return False
        if self.retrieval_score_gt is not None and not (rs > self.retrieval_score_gt):
            return False
        if self.retrieval_score_gte is not None and not (rs >= self.retrieval_score_gte):
            return False

        cc = clarify_count
        if self.clarify_count_lt is not None and not (cc < self.clarify_count_lt):
            return False
        if self.clarify_count_lte is not None and not (cc <= self.clarify_count_lte):
            return False
        if self.clarify_count_gt is not None and not (cc > self.clarify_count_gt):
            return False
        if self.clarify_count_gte is not None and not (cc >= self.clarify_count_gte):
            return False
        if self.clarify_count_eq is not None and not (cc == self.clarify_count_eq):
            return False

        return True


class PolicyRow(BaseModel):
    """单条 YAML 规则。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    condition: PolicyCondition
    action: str = Field(..., min_length=1)

    @field_validator("action")
    @classmethod
    def action_allowed(cls, v: str) -> str:
        allowed = {
            PolicyRoute.CLARIFY.value,
            PolicyRoute.DEGRADE.value,
            PolicyRoute.GENERATE.value,
        }
        if v not in allowed:
            raise ValueError(f"action must be one of {sorted(allowed)}, got {v!r}")
        return v


class PolicyFile(BaseModel):
    """单个 YAML 文件包装。"""

    model_config = ConfigDict(extra="ignore")

    version: int = 1
    rules: list[PolicyRow] = Field(default_factory=list)


@dataclass(frozen=True)
class PolicyEvaluationResult:
    action: str
    rule_name: str
    reason: str

    @property
    def is_default(self) -> bool:
        return self.rule_name == "default"
