from fastapi import APIRouter, Request
from app.wecom.crypto import decrypt_msg, encrypt_msg
from app.agent.core import run_agent
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/wecom/callback")
async def wecom_callback(request: Request):
    body = await request.body()

    msg_signature = request.query_params.get("msg_signature")
    timestamp = request.query_params.get("timestamp")
    nonce = request.query_params.get("nonce")

    # 1. 解密消息（返回已解析的字典）
    xml = decrypt_msg(body, msg_signature, timestamp, nonce)
    user_msg = xml.get("Content", "") if xml else ""
    user_id = xml.get("FromUserName", "anonymous") if xml else "anonymous"

    # 3. 调用 Agent
    reply = run_agent(user_id, user_msg)
    logger.info("run_agent called for user=%s", user_id)

    # 4. 加密返回
    return encrypt_msg(reply, xml, nonce, timestamp)

@router.get("/wecom/callback")
async def verify(request: Request):
    return request.query_params.get("echostr", "")