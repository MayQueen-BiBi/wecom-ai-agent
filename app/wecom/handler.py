"""
企微 HTTP 处理函数 re-export（实现见 ``app.wecom.entry``）。
"""
from __future__ import annotations

from app.wecom.entry import (
    handle_wecom_message,
    wecom_callback_get_verify,
    wecom_callback_post,
)

__all__ = [
    "handle_wecom_message",
    "wecom_callback_get_verify",
    "wecom_callback_post",
]
