import logging
from typing import Optional

import requests

from app.config.settings import QWEN_API_KEY

logger = logging.getLogger(__name__)

QWEN_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

FORBIDDEN_PHRASES = ["预约成功", "已为您预约", "挂号成功", "预约已完成"]


def validate_llm_response(response: str, session_state: str) -> str:
    """防止 LLM 在非完成状态下输出越权预约话术。"""
    if session_state != "appointment_completed":
        for phrase in FORBIDDEN_PHRASES:
            if phrase in response:
                return "我已记录您的需求，正在为您处理..."
    return response


def call_llm(system_prompt: str, user_prompt: str) -> str:
    if not QWEN_API_KEY:
        logger.warning("QWEN_API_KEY not configured, returning fallback response")
        return "暂时无法生成智能回复，请直接预约或咨询。"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {QWEN_API_KEY}",
    }

    payload = {
        "model": "qwen-flash",
        "input": {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        },
        "parameters": {"result_format": "message"},
    }

    try:
        resp = requests.post(QWEN_URL, headers=headers, json=payload, timeout=5)
        if resp.status_code == 200:
            result = resp.json()
            if "output" in result:
                return (
                    result["output"]["choices"][0]["message"]["content"].strip()
                )
        logger.error("LLM API returned non-200 status: %s", resp.status_code)
    except Exception as e:
        logger.error("LLM call error: %s", e)

    return "暂时无法生成回复，请稍后重试。"
