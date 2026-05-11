from __future__ import annotations

from typing import Tuple

from app.critic_rules.checks.common import CheckItemResult
from app.critic_rules.context import CriticContext

PRICE_HINTS: Tuple[str, ...] = ("元", "多少钱", "费用", "价格", "收费", "几千", "上万", "医保", "报销")
PAIN_HINTS: Tuple[str, ...] = ("疼", "痛", "麻醉", "不适", "怕疼", "止痛")


def check_intent_alignment(ctx: CriticContext, draft: str) -> Tuple[str, CheckItemResult]:
    """草稿主题须与 state.intent 一致（仅用草稿文本 + intent，不读 user_msg）。"""
    cid = "intent_alignment_draft_topics"
    intent = ctx.intent

    if intent == "pain_question":
        if any(p in draft for p in PRICE_HINTS) and not any(p in draft for p in PAIN_HINTS):
            safe = (
                "关于疼痛与麻醉方式，因人而异，一般会采取局部麻醉等措施减轻不适；"
                "具体感受需结合您的方案由医生面诊说明。"
            )
            return safe, CheckItemResult(cid, False, "replace", "pain_intent_price_dominated_draft")

    if intent == "price_question":
        if any(p in draft for p in PAIN_HINTS) and not any(p in draft for p in PRICE_HINTS):
            safe = (
                "关于费用需要结合检查方案与材料选择，线上无法给出确切金额；"
                "建议您到院面诊后由工作人员说明报价与支付方式。"
            )
            return safe, CheckItemResult(cid, False, "replace", "price_intent_pain_dominated_draft")

    return draft, CheckItemResult(cid, True, "none")
