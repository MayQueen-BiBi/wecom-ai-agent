"""
统一入口协议：所有渠道（WeCom / HTTP / 未来 SDK）使用相同请求与响应形状。

---------------------------------------------------------------------------
CONTRACT_VERSION = "7.6"

**DO NOT modify this contract without version bump**（字段增删、语义变更须升版
并同步 ``app/DEPENDENCY_RULES_FINAL.md`` / 客户端 SDK）。
---------------------------------------------------------------------------
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

CONTRACT_VERSION = "7.6"


@dataclass
class AgentRequest:
    user_id: str
    text: str
    channel: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """冻结对外形状：``reply`` + ``trace_id`` + ``success``；扩展字段放 ``extras``。"""

    reply: str
    trace_id: str
    success: bool
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowGraphResult:
    """``run_workflow_graph`` 内部结果，再映射为 :class:`AgentResponse`。"""

    final_response: str
    trace_id: str
    state: Dict[str, Any]
    trace: Dict[str, Any] = field(default_factory=dict)
