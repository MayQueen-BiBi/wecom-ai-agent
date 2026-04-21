from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_wecom_callback_post(monkeypatch):
    # mock 解密结果（模拟企微消息）
    monkeypatch.setattr(
        "app.wecom.handler.decrypt_msg",
        lambda body, sig, ts, nonce: {
            "FromUserName": "user_1",
            "ToUserName": "corp_1",
            "Content": "我想预约洗牙",
        },
    )

    # mock agent
    monkeypatch.setattr(
        "app.wecom.handler.run_agent",
        lambda user_id, msg: f"reply:{user_id}:{msg}",
    )

    # mock 加密返回
    monkeypatch.setattr(
        "app.wecom.handler.encrypt_msg",
        lambda reply, xml, nonce, ts: f"<xml>{reply}</xml>",
    )

    resp = client.post(
        "/wecom/callback?msg_signature=sig&timestamp=1&nonce=n",
        content=b"<xml>fake</xml>",
        headers={"Content-Type": "application/xml"},
    )

    assert resp.status_code == 200
    assert "reply:user_1:我想预约洗牙" in resp.text