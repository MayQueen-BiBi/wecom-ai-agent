"""
企业微信 Webhook：解密、校验、统一 ``AgentRequest`` 入口；异常永不裸奔。

路由注册在 ``app.main``；本模块仅导出处理函数。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from fastapi import Request
from fastapi.responses import PlainTextResponse, Response
from wechatpy.enterprise.crypto import WeChatCrypto

from app.api.entry import handle_request
from app.api.protocol import AgentRequest
from app.config.settings import AES_KEY, CORP_ID, TOKEN
from app.wecom.crypto import decrypt_msg, encrypt_msg

logger = logging.getLogger(__name__)


def parse_wecom_event(
    request: Request,
    raw_body: bytes,
) -> Tuple[Optional[AgentRequest], Optional[Dict[str, Any]]]:
    """
    将企微 POST 体解析为 :class:`AgentRequest`；失败返回 ``(None, None)``。

    ``msg`` 为解密后的 dict，供 ``encrypt_msg`` 回包使用。
    """
    try:
        raw_text = raw_body.decode("utf-8", errors="replace")
    except Exception:
        return None, None

    msg_signature = request.query_params.get("msg_signature")
    timestamp = request.query_params.get("timestamp")
    nonce = request.query_params.get("nonce")

    if "<xml>" not in raw_text:
        return None, None

    msg = decrypt_msg(raw_text, msg_signature, timestamp, nonce)
    if not msg:
        return None, None

    user_id = str(msg.get("from") or "").strip()
    text = str(msg.get("content") or "").strip()
    req = AgentRequest(
        user_id=user_id,
        text=text,
        channel="wecom",
        metadata={
            "wecom_msg_type": msg.get("msg_type"),
            "raw_keys": list(msg.keys()),
        },
    )
    return req, msg


async def wecom_callback_post(request: Request) -> Response:
    """POST ``/wecom/callback``：异常保护 + 无效请求降级 + 永远返回可回传内容。"""
    try:
        raw_body = await request.body()
        echostr = request.query_params.get("echostr")
        if echostr:
            return Response(content=echostr)

        req, msg = parse_wecom_event(request, raw_body)
        nonce = request.query_params.get("nonce")
        timestamp = request.query_params.get("timestamp")

        if req is None or not str(req.text or "").strip():
            logger.info("wecom invalid or empty body; ack success")
            return Response(content="success")

        res = await handle_request(req)
        reply_text = res.reply or "系统繁忙，请稍后再试"

        if msg is None:
            return Response(content="success")

        try:
            encrypted = encrypt_msg(reply_text, msg, nonce, timestamp)
            return Response(content=encrypted, media_type="application/xml")
        except Exception as enc_err:
            logger.exception("wecom encrypt failed: %s", enc_err)
            return Response(content="success")

    except Exception as e:
        logger.exception("wecom_callback_post fatal: %s", e)
        return Response(content="success")


async def wecom_callback_get_verify(request: Request) -> PlainTextResponse:
    """GET ``/wecom/callback``：URL 验证。"""
    msg_signature = request.query_params.get("msg_signature")
    timestamp = request.query_params.get("timestamp")
    nonce = request.query_params.get("nonce")
    echostr = request.query_params.get("echostr")

    if echostr and not msg_signature:
        return PlainTextResponse(echostr)

    crypto = WeChatCrypto(TOKEN, AES_KEY, CORP_ID)
    try:
        echo_str = crypto.check_signature(msg_signature, timestamp, nonce, echostr)
        return PlainTextResponse(echo_str)
    except Exception as e:
        logger.warning("wecom verify error: %s", e)
        return PlainTextResponse("error")


async def handle_wecom_message(event: Dict[str, Any]) -> str:
    """解密后的消息 dict → 回复文本（测试或内部复用）。"""
    req = AgentRequest(
        user_id=str(event.get("from") or ""),
        text=str(event.get("content") or ""),
        channel="wecom",
        metadata={"wecom_msg_type": event.get("msg_type")},
    )
    if not req.text.strip():
        return "无效请求"
    try:
        res = await handle_request(req)
        return res.reply
    except Exception as e:
        logger.exception("handle_wecom_message: %s", e)
        return "系统繁忙，请稍后再试"
