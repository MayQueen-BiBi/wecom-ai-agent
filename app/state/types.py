"""分层状态字段的 TypedDict 文档（运行态以 AgentRunState 为准）。"""
from typing import Any, Dict, List, TypedDict


class AgentStateLayered(TypedDict, total=False):
    user_id: str
    user_msg: str
    intent: str
    rewritten_query: str
    risk_level: str
    legacy_intent: str
    merged_retrieval_query: str
    medical_context: str
    contexts: List[str]
    retrieval_score: float
    clarify_count: int
    route: str
    action: str
    trace: Dict[str, Any]
