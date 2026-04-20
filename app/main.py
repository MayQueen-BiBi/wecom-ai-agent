from fastapi import FastAPI
from app.wecom.handler import router as wecom_router

app = FastAPI()

app.include_router(wecom_router)

@app.get("/")
def health():
    return {"status": "ok"}