"""
Schema-first：统一语义理解的结构化输出（Understanding Layer 唯一对外契约）。
下游 retrieval / routing / execution / critic 只消费本模型字段，禁止再解析自然语言意图。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

# 对话阶段（策略层可消费，非动作决策）
CONVERSATION_STAGES: Tuple[str, ...] = (
    "discovery",
    "consideration",
    "concern",
    "transactional",
    "support",
)

RISK_LEVELS: Tuple[str, ...] = ("Level 1", "Level 2", "Level 3")

V3_INTENTS: Tuple[str, ...] = (
    "medical_consulting",
    "price_question",
    "pain_question",
    "recovery_question",
    "appointment",
    "insurance",
    "comparative",
    "logistics",
    "out_of_scope",
)


@dataclass(frozen=True)
class UnderstandingResult:
    """Unified Understanding Node 的单一输出。"""

    intent: str
    entities: Dict[str, Any]
    rewritten_query: str
    risk_level: str
    conversation_stage: str
    confidence: float
    raw_llm: Optional[Dict[str, Any]] = None

    def to_trace_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "entities": self.entities,
            "rewritten_query": self.rewritten_query,
            "risk_level": self.risk_level,
            "conversation_stage": self.conversation_stage,
            "confidence": self.confidence,
        }

    @staticmethod
    def infer_conversation_stage(intent: str) -> str:
        """意图 → 阶段（规则，非 LLM）；LLM 未返回 stage 时使用。"""
        if intent == "appointment":
            return "transactional"
        if intent in ("price_question", "comparative", "insurance"):
            return "consideration"
        if intent in ("pain_question", "recovery_question"):
            return "concern"
        if intent in ("logistics", "out_of_scope"):
            return "support"
        return "discovery"

    @classmethod
    def normalize(
        cls,
        intent: str,
        rewritten_query: str,
        risk_level: str,
        *,
        entities: Optional[Dict[str, Any]] = None,
        conversation_stage: Optional[str] = None,
        confidence: Optional[float] = None,
        raw_llm: Optional[Dict[str, Any]] = None,
        user_msg_for_entities: str = "",
    ) -> "UnderstandingResult":
        intent = intent if intent in V3_INTENTS else "medical_consulting"
        rq = (rewritten_query or "").strip() or user_msg_for_entities
        risk = risk_level if risk_level in RISK_LEVELS else "Level 2"
        stage = conversation_stage or cls.infer_conversation_stage(intent)
        if stage not in CONVERSATION_STAGES:
            stage = cls.infer_conversation_stage(intent)
        conf = 0.85 if confidence is None else max(0.0, min(1.0, float(confidence)))
        ent: Dict[str, Any] = dict(entities) if entities else {}
        return cls(
            intent=intent,
            entities=ent,
            rewritten_query=rq,
            risk_level=risk,
            conversation_stage=stage,
            confidence=conf,
            raw_llm=raw_llm,
        )
