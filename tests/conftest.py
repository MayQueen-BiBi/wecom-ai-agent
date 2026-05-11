import os
import sys
from pathlib import Path

# 企微加解密模块在 import 时校验环境变量；CI / 冒烟需占位值（43 位 AES key）。
if not os.environ.get("WECOM_TOKEN"):
    os.environ["WECOM_TOKEN"] = "pytest_wec_token"
if not os.environ.get("WECOM_AES_KEY"):
    os.environ["WECOM_AES_KEY"] = "0" * 43
if not os.environ.get("WECOM_CORP_ID"):
    os.environ["WECOM_CORP_ID"] = "pytest_corp_id"

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
