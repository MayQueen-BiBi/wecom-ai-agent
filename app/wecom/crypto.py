import time
import xml.etree.ElementTree as ET
from wechatpy.enterprise.crypto import WeChatCrypto
from app.config.settings import TOKEN, AES_KEY, CORP_ID, validate_settings

validate_settings()

crypto = WeChatCrypto(TOKEN, AES_KEY, CORP_ID)


def decrypt_msg(raw_body, msg_signature, timestamp, nonce):
    print("Raw body received:", raw_body)

    try:
        # ✅ 正确：直接解密整个XML
        xml_str = crypto.decrypt_message(
            raw_body,
            msg_signature,
            timestamp,
            nonce
        )

        print("Decrypted XML:", xml_str)

        root = ET.fromstring(xml_str)

        return {
            "from": root.find("FromUserName").text,
            "to": root.find("ToUserName").text,
            "content": root.find("Content").text if root.find("Content") is not None else "",
            "msg_type": root.find("MsgType").text
        }

    except Exception as e:
        print("decrypt_msg error:", repr(e))
        return None


def encrypt_msg(reply_text, msg, nonce, timestamp):
    reply_xml = f"""
    <xml>
        <ToUserName><![CDATA[{msg["from"]}]]></ToUserName>
        <FromUserName><![CDATA[{msg["to"]}]]></FromUserName>
        <CreateTime>{int(time.time())}</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[{reply_text}]]></Content>
    </xml>
    """

    return crypto.encrypt_message(
        reply_xml,
        nonce,
        timestamp
    )