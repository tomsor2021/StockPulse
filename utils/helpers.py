"""通用工具函数"""
from datetime import date, datetime, timedelta
from typing import Optional
import re


def today_str() -> str:
    return date.today().isoformat()


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_pct(value: Optional[float], digits: int = 2) -> str:
    if value is None:
        return "--"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{digits}f}%"


def format_money(value: Optional[float]) -> str:
    if value is None:
        return "--"
    if abs(value) >= 100000000:
        return f"{value / 100000000:.2f}亿"
    elif abs(value) >= 10000:
        return f"{value / 10000:.2f}万"
    return f"{value:.2f}"


def format_volume(value: Optional[float]) -> str:
    if value is None:
        return "--"
    if abs(value) >= 100000000:
        return f"{value / 100000000:.2f}亿"
    elif abs(value) >= 10000:
        return f"{value / 10000:.2f}万"
    return f"{value:.0f}"


def is_trading_time() -> bool:
    """判断当前是否为A股交易时段（简化版）"""
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.hour * 100 + now.minute
    return (930 <= t <= 1130) or (1300 <= t <= 1500)


def parse_stock_code(code: str) -> str:
    """标准化股票代码（支持A股6位和港股5位）"""
    code = code.strip().upper().replace(".SZ", "").replace(".SH", "").replace(".HK", "")
    # 优先匹配6位A股代码
    match = re.search(r'(\d{6})', code)
    if match:
        return match.group(1)
    # 匹配5位港股代码
    match = re.search(r'(\d{5})', code)
    if match:
        return match.group(1)
    return code


def make_sentience_label(value: Optional[str]) -> str:
    labels = {"乐观": "😊 乐观", "谨慎": "🤔 谨慎", "悲观": "😟 悲观", "极端恐慌": "😱 极端恐慌"}
    return labels.get(value, value or "--")


def days_between(d1: str, d2: str) -> int:
    return (date.fromisoformat(d2) - date.fromisoformat(d1)).days


def truncate_text(text: Optional[str], max_len: int = 50) -> str:
    if not text:
        return ""
    text = text.strip()
    return text if len(text) <= max_len else text[:max_len] + "..."
