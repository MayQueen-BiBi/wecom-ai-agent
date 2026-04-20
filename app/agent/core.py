import json
import requests
from app.agent.tools import tools, call_tool
from app.config.settings import QWEN_API_KEY


QWEN_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"


def run_agent(user_msg: str):
    """
    Qwen Flash Agent（支持工具调用）
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {QWEN_API_KEY}"
    }

    payload = {
        "model": "qwen-flash",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "你是牙科诊所客服，负责预约。必须通过工具完成预约，不允许编造时间。"
                },
                {
                    "role": "user",
                    "content": user_msg
                }
            ]
        },
        "parameters": {
            "result_format": "message"
        }
    }

    resp = requests.post(QWEN_URL, headers=headers, json=payload)
    result = resp.json()

    msg = result["output"]["choices"][0]["message"]

    # =========================
    # 1️⃣ 如果模型要调用工具
    # =========================
    if "tool_calls" in msg and msg["tool_calls"]:
        tool_call = msg["tool_calls"][0]

        func_name = tool_call["function"]["name"]
        args = json.loads(tool_call["function"]["arguments"])

        tool_result = call_tool(func_name, args)

        # =========================
        # 2️⃣ 把工具结果再喂回模型
        # =========================
        payload["input"]["messages"].append(msg)
        payload["input"]["messages"].append({
            "role": "tool",
            "content": str(tool_result)
        })

        resp2 = requests.post(QWEN_URL, headers=headers, json=payload)
        result2 = resp2.json()

        return result2["output"]["choices"][0]["message"]["content"]

    # =========================
    # 3️⃣ 普通回复
    # =========================
    return msg["content"]