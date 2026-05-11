from app.observability.logging_config import configure_logging

configure_logging()

from fastapi import FastAPI, Request

from app.api.entry import handle_request
from app.api.protocol import AgentRequest
from app.wecom.entry import wecom_callback_get_verify, wecom_callback_post

app = FastAPI()


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/wecom/callback")
async def wecom_post_entry(request: Request):
    return await wecom_callback_post(request)


@app.get("/wecom/callback")
async def wecom_get_entry(request: Request):
    return await wecom_callback_get_verify(request)


@app.get("/dev/chat")
async def dev_chat(msg: str = "我想预约洗牙", user_id: str = "browser_demo"):
    """
    浏览器/本地调试：经统一协议入口；生产请删除或加鉴权。
    """
    req = AgentRequest(user_id=user_id, text=msg, channel="http_dev", metadata={})
    res = await handle_request(req)
    return {
        "user_id": user_id,
        "input": msg,
        "reply": res.reply,
        "trace_id": res.trace_id,
        "success": res.success,
    }
