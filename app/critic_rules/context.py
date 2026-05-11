"""Critic 输入：仅来自 structured state + 待审草稿，不解析用户 query。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.state.agent_run_state import AgentRunState


@dataclass(frozen=True)
class CriticContext:
    intent: str
    risk_level: str
    retrieval_score: float
    contexts: tuple[str, ...]

    @classmethod
    def from_run_state(cls, state: "AgentRunState") -> "CriticContext":
        ctxs = state.contexts or []
        return cls(
            intent=(state.intent or "").strip() or "medical_consulting",
            risk_level=state.risk_level or "Level 2",
            retrieval_score=float(state.retrieval_score or 0.0),
            contexts=tuple(ctxs),
        )
