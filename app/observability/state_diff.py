"""
``AgentRunState`` 等 dataclass 的轻量结构化 diff，供 graph 每步后观测。
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any, Dict


def diff_state(old: Any, new: Any) -> Dict[str, Any]:
    """
    返回 ``{"changed": {field: {"old": ..., "new": ...}}, "changed_count": n}``。

    非 dataclass 或类型不一致时返回带 ``error`` 键的字典。
    """
    if old is None or new is None:
        return {"error": "missing_state", "changed": {}, "changed_count": 0}
    if type(old) is not type(new):
        return {
            "error": "type_mismatch",
            "old_type": type(old).__name__,
            "new_type": type(new).__name__,
            "changed": {},
            "changed_count": 0,
        }
    if not is_dataclass(old):
        return {"error": "not_dataclass", "changed": {}, "changed_count": 0}

    changed: Dict[str, Dict[str, Any]] = {}
    for f in fields(old):
        a = getattr(old, f.name)
        b = getattr(new, f.name)
        if a != b:
            changed[f.name] = {"old": a, "new": b}
    return {"changed": changed, "changed_count": len(changed)}
