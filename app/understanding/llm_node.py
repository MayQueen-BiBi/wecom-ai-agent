"""
Unified Understanding 的唯一 LLM 入口：输出符合 UnderstandingResult 的 JSON。
不做路由/检索/生成；无 Key 时规则兜底。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

import requests

from app.config.settings import QWEN_API_KEY
from app.understanding.extraction import extract_slots
from app.understanding.schemas import (
    CONVERSATION_STAGES,
    RISK_LEVELS,
    UnderstandingResult,
    V3_INTENTS,
)

logger = logging.getLogger(__name__)

QWEN_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"


def _parse_json_block(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return None


def _fallback_understanding(user_msg: str, last_user_snippet: str) -> UnderstandingResult:
    combined = f"{last_user_snippet} {user_msg}".strip() if last_user_snippet else user_msg
    intent = "medical_consulting"
    risk = "Level 2"
    rq = combined

    if any(w in user_msg for w in ["预约", "挂号", "面诊", "安排时间", "想去看牙"]):
        intent, risk, rq = "appointment", "Level 1", combined
    elif any(w in user_msg for w in ["在哪", "地址", "停车", "营业时间", "几点"]):
        intent, risk, rq = "logistics", "Level 1", combined
    elif any(w in user_msg for w in ["医保", "报销", "社保"]):
        intent, risk, rq = "insurance", "Level 1", combined
    elif any(w in user_msg for w in ["多少钱", "价格", "费用", "贵吗", "收费"]):
        intent, risk, rq = "price_question", "Level 1", combined
    elif any(w in user_msg for w in ["疼吗", "怕疼", "疼不疼", "痛吗"]):
        intent, risk = "pain_question", "Level 2"
        rq = combined if len(user_msg) <= 8 else user_msg
    elif any(w in user_msg for w in ["多久", "恢复", "几天", "复查"]):
        intent, risk, rq = "recovery_question", "Level 2", combined
    elif any(w in user_msg for w in ["对比", "哪个好", "国产", "进口", "韩国", "瑞士"]):
        intent, risk, rq = "comparative", "Level 1", combined
    elif any(w in user_msg for w in ["出血", "感染", "肿得厉害", "急诊"]):
        intent, risk, rq = "medical_consulting", "Level 3", combined

    slots = extract_slots(user_msg)
    return UnderstandingResult.normalize(
        intent,
        rq,
        risk,
        entities=slots,
        confidence=0.75,
        raw_llm=None,
        user_msg_for_entities=user_msg,
    )


def run_unified_semantic_understanding(
    user_msg: str,
    last_user_message: Optional[str] = None,
) -> UnderstandingResult:
    """
    单次语义理解：intent + entities + rewritten_query + risk_level + conversation_stage + confidence。
    """
    last = last_user_message or ""
    if not QWEN_API_KEY:
        return _fallback_understanding(user_msg, last)

    ctx = f"上一轮用户原话：{last}\n" if last else ""

    schema_desc = json.dumps(
        {
            "intent": f"str, one of {list(V3_INTENTS)}",
            "rewritten_query": "str, 完整检索用中文问句",
            "risk_level": f"str, one of {list(RISK_LEVELS)}",
            "entities": "object, 可选：phone/name/service_type 等槽位",
            "conversation_stage": f"str, one of {list(CONVERSATION_STAGES)}",
            "confidence": "number 0~1",
        },
        ensure_ascii=False,
    )

    system = f"""你是牙科智能客服的「统一语义理解」模块。只输出一个 JSON 对象，不要 markdown，不要解释。

必须字段与类型：
- intent: {", ".join(V3_INTENTS)}
- rewritten_query: 结合上下文改写后的完整检索语句（中文）；短句如「疼吗」要补全所指治疗项目。
- risk_level: Level 1（价格/流程/地址） | Level 2（疼痛/恢复/适应症） | Level 3（急性出血/感染/急诊）
- entities: 对象，从用户话中提取的结构化槽位（如 phone、name、service_type），无则 {{}}。
- conversation_stage: discovery | consideration | concern | transactional | support（与意图一致即可）
- confidence: 0 到 1 的小数，表示你对以上字段的整体置信度

Few-shot:
用户：（上一轮讨论种植牙）当前：疼吗
{{"intent":"pain_question","rewritten_query":"种植牙手术过程是否疼痛、术后疼痛程度","risk_level":"Level 2","entities":{{}},"conversation_stage":"concern","confidence":0.88}}

用户：多少钱
{{"intent":"price_question","rewritten_query":"牙科治疗项目价格费用咨询","risk_level":"Level 1","entities":{{}},"conversation_stage":"consideration","confidence":0.9}}

字段说明摘要：{schema_desc}
"""

    user_block = f"{ctx}当前用户输入：{user_msg}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {QWEN_API_KEY}",
    }
    payload = {
        "model": "qwen-flash",
        "input": {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_block},
            ]
        },
        "parameters": {"result_format": "message", "temperature": 0.1},
    }

    try:
        resp = requests.post(QWEN_URL, headers=headers, json=payload, timeout=12)
        if resp.status_code != 200:
            logger.warning("unified_semantic_understanding HTTP %s", resp.status_code)
            return _fallback_understanding(user_msg, last)
        result = resp.json()
        content = result["output"]["choices"][0]["message"]["content"].strip()
        data = _parse_json_block(content)
        if not data:
            return _fallback_understanding(user_msg, last)

        intent = str(data.get("intent", "medical_consulting"))
        rq = str(data.get("rewritten_query", user_msg)).strip() or user_msg
        risk = str(data.get("risk_level", "Level 2"))
        ent = data.get("entities")
        if not isinstance(ent, dict):
            ent = extract_slots(user_msg)
        else:
            merged = extract_slots(user_msg)
            merged.update({k: v for k, v in ent.items() if v})
            ent = merged
        stage = data.get("conversation_stage")
        if isinstance(stage, str):
            stage = stage.strip()
        else:
            stage = None
        conf = data.get("confidence")
        try:
            conf_f = float(conf) if conf is not None else None
        except (TypeError, ValueError):
            conf_f = None

        return UnderstandingResult.normalize(
            intent,
            rq,
            risk,
            entities=ent,
            conversation_stage=stage,
            confidence=conf_f,
            raw_llm=data,
            user_msg_for_entities=user_msg,
        )
    except Exception as e:
        logger.exception("unified_semantic_understanding failed: %s", e)
        return _fallback_understanding(user_msg, last)
