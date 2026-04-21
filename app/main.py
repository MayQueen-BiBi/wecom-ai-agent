from fastapi import FastAPI
from app.wecom.handler import router as wecom_router
from app.agent.core import run_agent

app = FastAPI()

app.include_router(wecom_router)


@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/dev/chat")
def dev_chat(msg: str = "我想预约洗牙", user_id: str = "browser_demo"):
    """
    浏览器/本地调试：不走企微加解密，直接调用 run_agent。
    生产环境请删除本路由或加鉴权。
    """
    reply = run_agent(user_id, msg)
    return {"user_id": user_id, "input": msg, "reply": reply}