"""
单次用户回合的运行态（分层 Agent 各层只读写此对象）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentRunState:
    """一次用户回合的可变状态容器。"""

    user_id: str
    user_msg: str

    intent: str = ""
    rewritten_query: str = ""
    risk_level: str = "Level 2"
    legacy_intent: str = ""

    # Unified Understanding 结构化输出（下游只读，禁止再解析 user_msg 意图）
    entities: Dict[str, Any] = field(default_factory=dict)
    conversation_stage: str = ""
    understanding_confidence: float = 0.0

    merged_retrieval_query: str = ""
    contexts: List[str] = field(default_factory=list)
    retrieval_score: float = 0.0

    clarify_count: int = 0

    route: str = ""
    action: str = ""

    final_response: Optional[str] = None
    early_exit: bool = False

    # 由 execution reducer 写入；workflow 负责 flush 到 session_store（execution 不直连 session）
    session_updates: List[Dict[str, Any]] = field(default_factory=list)

    trace: Dict[str, Any] = field(default_factory=dict)

    def to_trace_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "legacy_intent": self.legacy_intent,
            "rewritten_query": self.rewritten_query,
            "risk_level": self.risk_level,
            "entities": self.entities,
            "conversation_stage": self.conversation_stage,
            "understanding_confidence": self.understanding_confidence,
            "merged_retrieval_query": self.merged_retrieval_query,
            "retrieval_score": self.retrieval_score,
            "clarify_count": self.clarify_count,
            "route": self.route,
            "action": self.action,
            "num_contexts": len(self.contexts),
        }
