import os

TOKEN = os.getenv("WECOM_TOKEN", "")
AES_KEY = os.getenv("WECOM_AES_KEY", "")
CORP_ID = os.getenv("WECOM_CORP_ID", "")
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")

# 可选：会话状态（澄清计数等）持久化到 Redis
REDIS_URL = os.getenv("REDIS_URL", "").strip()
REDIS_KEY_PREFIX = os.getenv("REDIS_KEY_PREFIX", "wecom_ai:").strip()
REDIS_SESSION_TTL = int(os.getenv("REDIS_SESSION_TTL", "604800"))


def validate_settings() -> None:
    missing = []
    if not TOKEN:
        missing.append("WECOM_TOKEN")
    if not AES_KEY:
        missing.append("WECOM_AES_KEY")
    if not CORP_ID:
        missing.append("WECOM_CORP_ID")

    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    # 企业微信 EncodingAESKey 是 43 位（后台展示通常不带末尾 '='）
    # 这里做提前校验，避免在 wechatpy 内部抛出不直观的 Incorrect padding。
    aes_key = AES_KEY.strip()
    if len(aes_key) != 43:
        raise RuntimeError(
            "Invalid WECOM_AES_KEY: expected 43 chars EncodingAESKey from WeCom."
        )
