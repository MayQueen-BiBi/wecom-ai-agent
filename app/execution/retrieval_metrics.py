"""检索质量分数（供 Routing Policy 使用，无 LLM）。"""
from __future__ import annotations

from typing import List


def compute_retrieval_score(contexts: List[str]) -> float:
    """
    简单可解释得分 ∈ [0,1]：有文档则基于总字数归一；无文档为 0。
    """
    if not contexts:
        return 0.0
    total_chars = sum(len((c or "").strip()) for c in contexts)
    if total_chars == 0:
        return 0.0
    # 短 FAQ 也给最低非零分，避免「有一条但很短的答案」被判 0
    base = min(1.0, 0.15 + min(total_chars / 800.0, 0.85))
    return round(base, 4)
