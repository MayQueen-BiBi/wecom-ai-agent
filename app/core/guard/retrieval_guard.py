"""检索守卫：命中不足时禁止自由生成，进入澄清或降级路径。"""
from typing import List, Tuple


def _has_usable_context(contexts: List[str], min_total: int = 8) -> bool:
    if not contexts:
        return False
    joined = "".join(contexts)
    return len(joined.strip()) >= min_total


def retrieval_gate(
    contexts: List[str],
    clarify_count: int,
    max_clarify: int = 2,
) -> Tuple[str, str]:
    """
    返回 (mode, reason)
    mode: ok | clarify | degrade
    """
    if contexts and _has_usable_context(contexts):
        return "ok", ""

    if clarify_count < max_clarify:
        return "clarify", "retrieval_miss"

    return "degrade", "retrieval_miss_max_clarify"


def clarification_prompt(prev_query: str) -> str:
    return (
        "我这边没有完全匹配的官方说明。为避免误导，想先确认一下："
        "您主要想了解哪一类问题（例如：种植牙 / 正畸 / 洗牙 / 牙痛）？"
        "或直接留下联系方式，我们安排医护与您沟通。"
    )


def degrade_response() -> str:
    return (
        "根据当前知识库暂时无法精准回答该问题。建议您到院由医生面诊评估；"
        "如需预约或转人工客服，也可以直接告诉我。"
    )
