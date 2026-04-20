from fastapi import APIRouter, Request
from app.wecom.crypto import decrypt_msg, encrypt_msg
from app.agent.core import run_agent
import time

router = APIRouter()

@router.post("/wecom/callback")
async def wecom_callback(request: Request):
    body = await request.body()

    msg_signature = request.query_params.get("msg_signature")
    timestamp = request.query_params.get("timestamp")
    nonce = request.query_params.get("nonce")

    # 1. 解密（必须返回 XML 字符串）
    xml_str = decrypt_msg(body, msg_signature, timestamp, nonce)

    # 2. 解析 XML
    import xml.etree.ElementTree as ET
    xml = ET.fromstring(xml_str)

    user_msg = xml.find("Content").text

    # 3. 调用 Agent
    reply = run_agent(user_msg)

    # 4. 加密返回
    return encrypt_msg(reply, nonce, timestamp)

@router.get("/wecom/callback")
async def verify(request: Request):
    return request.query_params.get("echostr", "")