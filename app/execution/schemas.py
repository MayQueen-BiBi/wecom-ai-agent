"""Execution 层标准化结果（纯数据）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class ExecutionResult:
    response: str
    contexts: List[str]
    trace: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)
