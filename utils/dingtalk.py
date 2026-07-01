"""钉钉机器人消息推送"""
import logging
import json
import requests
from typing import Optional

logger = logging.getLogger("stockpulse.dingtalk")


def send_dingtalk_message(webhook_url: str, message: str, msg_type: str = "text") -> bool:
    """发送钉钉消息"""
    if not webhook_url or not webhook_url.startswith("https://"):
        logger.warning("钉钉 Webhook URL 无效")
        return False
    try:
        if msg_type == "text":
            payload = {"msgtype": "text", "text": {"content": message}}
        elif msg_type == "markdown":
            payload = {"msgtype": "markdown", "markdown": {"title": "股票复盘提醒", "text": message}}
        else:
            payload = {"msgtype": "text", "text": {"content": message}}

        resp = requests.post(webhook_url, json=payload, timeout=10)
        result = resp.json()
        if result.get("errcode") == 0:
            logger.info("钉钉消息发送成功")
            return True
        else:
            logger.warning(f"钉钉消息发送失败: {result}")
            return False
    except requests.RequestException as e:
        logger.warning(f"钉钉消息发送异常: {e}")
        return False


def send_alert_notification(webhook_url: str, stock_name: str, alert_type: str, message: str):
    """发送提醒通知到钉钉"""
    type_labels = {
        "up_limit": "📈 涨停提醒",
        "down_limit": "📉 跌停提醒",
        "volume_spike": "📊 放量异动",
        "price_break": "🔻 破位提醒",
        "custom": "📌 自定义提醒",
    }
    title = type_labels.get(alert_type, "📌 提醒")
    content = f"### {title}\n- **个股**: {stock_name}\n- **详情**: {message}\n- **时间**: {__import__('datetime').datetime.now().strftime('%H:%M:%S')}"
    return send_dingtalk_message(webhook_url, content, msg_type="markdown")
