"""Understanding 层协议（边界冻结；实现可逐步对齐）。"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.state.agent_run_state import AgentRunState
from app.understanding.schemas import UnderstandingResult


@runtime_checkable
class UnderstandingEngine(Protocol):
    async def understand(self, state: AgentRunState) -> UnderstandingResult:
        """由 `AgentRunState` 提供 user_msg 等只读上下文，返回结构化理解结果。"""
        ...
