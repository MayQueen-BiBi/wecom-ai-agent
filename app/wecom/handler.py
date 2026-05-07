from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, Response
from wechatpy.enterprise.crypto import WeChatCrypto
from app.config.settings import TOKEN, AES_KEY, CORP_ID
from app.wecom.crypto import decrypt_msg, encrypt_msg
from app.agent.core import run_agent
import logging
import xmltodict

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/wecom/callback")
async def callback(request: Request):

    raw_body = (await request.body()).decode()

    msg_signature = request.query_params.get("msg_signature")
    timestamp = request.query_params.get("timestamp")
    nonce = request.query_params.get("nonce")
    echostr = request.query_params.get("echostr")

    # 1.URL验证优先级最高
    if echostr:
        return Response(content=echostr)

    # 2.只有XML才进入解密
    if "<xml>" not in raw_body:
        print("Not xml request, ignore")
        return Response(content="success")

    # 3.解密消息
    msg = decrypt_msg(raw_body, msg_signature, timestamp, nonce)

    if not msg:
        return Response(content="success")

    print("USER MSG:", msg)

    user_id = msg["from"]
    user_text = msg["content"]

    print("USER:", user_id, user_text)

    # =========================
    # 3️⃣ 调用你的 run_agent
    # =========================
    reply_text = run_agent(user_id, user_text)

    print("REPLY:", reply_text)

    # =========================
    # 3️⃣ 回复
    # =========================
    reply = encrypt_msg(
        reply_text,
        msg,
        nonce,
        timestamp
    )

    return Response(content=reply, media_type="application/xml")


@router.get("/wecom/callback")
async def verify(request: Request):
    msg_signature = request.query_params.get("msg_signature")
    timestamp = request.query_params.get("timestamp")
    nonce = request.query_params.get("nonce")
    echostr = request.query_params.get("echostr")

    # 🟢 测试模式：只要有 echostr 直接返回
    if echostr and not msg_signature:
        return PlainTextResponse(echostr)

    print(
        TOKEN, AES_KEY, CORP_ID, msg_signature, timestamp, nonce, echostr
    )
    # 🔴 企业微信正式模式：
    crypto = WeChatCrypto(TOKEN, AES_KEY, CORP_ID)
    try:
        echo_str = crypto.check_signature(
            msg_signature,
            timestamp,
            nonce,
            echostr
        )
        return PlainTextResponse(echo_str)

    except Exception as e:
        print("VERIFY ERROR:", repr(e))
        return PlainTextResponse("error")

