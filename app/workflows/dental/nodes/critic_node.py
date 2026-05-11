"""critic：当前内嵌于 core_executor 生成路径；本节点占位透传。"""
from __future__ import annotations

from app.state.agent_run_state import AgentRunState


async def run(state: AgentRunState) -> AgentRunState:
    return state
