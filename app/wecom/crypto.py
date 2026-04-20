from wechatpy.enterprise.crypto import WeChatCrypto
from app.config.settings import TOKEN, AES_KEY, CORP_ID
crypto = WeChatCrypto(TOKEN, AES_KEY, CORP_ID)
import time
import xml.etree.ElementTree as ET


def decrypt_msg(raw_body, msg_signature, timestamp, nonce):
    """
    微信 -> 你（解密）
    """
    xml_str = crypto.decrypt_message(
        raw_body,
        msg_signature,
        timestamp,
        nonce
    )

    xml = ET.fromstring(xml_str)

    return {
        "FromUserName": xml.find("FromUserName").text,
        "ToUserName": xml.find("ToUserName").text,
        "Content": xml.find("Content").text
    }


def encrypt_msg(reply_text, xml, nonce, timestamp):
    """
    你 -> 微信（加密回复）
    """

    reply_xml = f"""
    <xml>
        <ToUserName><![CDATA[{xml["FromUserName"]}]]></ToUserName>
        <FromUserName><![CDATA[{xml["ToUserName"]}]]></FromUserName>
        <CreateTime>{int(time.time())}</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[{reply_text}]]></Content>
    </xml>
    """

    encrypted_xml = crypto.encrypt_message(
        reply_xml,
        nonce,
        timestamp
    )

    return encrypted_xml