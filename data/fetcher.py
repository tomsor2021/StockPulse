"""数据获取：AKShare 实时行情、Baostock 日K线"""
import logging
import time
import pandas as pd
from datetime import date

logger = logging.getLogger("stockpulse.fetcher")
_last_request_time = 0.0


def _rate_limit():
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < 0.5:
        time.sleep(0.5 - elapsed)
    _last_request_time = time.time()


def _safe_fetch(func, *args, retries=2, **kwargs):
    for attempt in range(retries + 1):
        try:
            _rate_limit()
            result = func(*args, **kwargs)
            if result is not None and hasattr(result, 'empty') and not result.empty:
                return result
        except Exception as e:
            logger.warning(f"API请求失败(尝试{attempt+1}/{retries+1}): {e}")
            if attempt < retries:
                time.sleep(2)
    return None


def _get_akshare():
    import akshare as ak
    return ak


def fetch_market_overview():
    try:
        ak = _get_akshare()
        df = _safe_fetch(ak.stock_zh_a_spot_em, retries=2)
        if df is None or df.empty:
            return None
        return {
            "total": len(df),
            "up": int((df["涨跌幅"] > 0).sum()),
            "down": int((df["涨跌幅"] < 0).sum()),
            "limit_up": int((df["涨跌幅"] >= 9.8).sum()),
            "limit_down": int((df["涨跌幅"] <= -9.8).sum()),
            "date": str(date.today()),
        }
    except Exception as e:
        logger.error(f"获取市场总览失败: {e}")
        return None


def fetch_limit_up_pool():
    try:
        ak = _get_akshare()
        return _safe_fetch(ak.stock_zt_pool_em, retries=2)
    except Exception as e:
        logger.warning(f"获取涨停板数据失败: {e}")
        return None


def fetch_board_industry():
    try:
        ak = _get_akshare()
        return _safe_fetch(ak.stock_board_industry_name_em, retries=2)
    except Exception as e:
        logger.warning(f"获取板块行情失败: {e}")
        return None


def fetch_stock_spot(codes=None):
    try:
        ak = _get_akshare()
        df = _safe_fetch(ak.stock_zh_a_spot_em, retries=2)
        if df is not None and codes:
            df = df[df["代码"].str[:6].isin(codes)]
        return df
    except Exception as e:
        logger.error(f"获取个股行情失败: {e}")
        return None


def fetch_stock_name(code):
    try:
        ak = _get_akshare()
        df = _safe_fetch(ak.stock_zh_a_spot_em, retries=1)
        if df is not None:
            match = df[df["代码"].str[:6] == code]
            if not match.empty:
                return str(match.iloc[0].get("名称", ""))
        return None
    except Exception:
        return None


def fetch_kline_data(code, start_date, end_date=None, freq="d"):
    import baostock as bs
    if end_date is None:
        end_date = date.today().isoformat()
    try:
        bs.login()
        bs_code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
        rs = bs.query_history_k_data_plus(
            bs_code,
            fields="date,open,high,low,close,volume,amount,pctChg",
            start_date=start_date, end_date=end_date,
            frequency=freq, adjustflag="2",
        )
        rows = []
        while rs.next():
            row = rs.get_row_data()
            if row[0]:
                rows.append(row)
        bs.logout()
        if not rows:
            return None
        import pandas as pd
        df = pd.DataFrame(rows, columns=["date","open","high","low","close","volume","amount","pctChg"])
        for col in ["open","high","low","close","volume","amount","pctChg"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date")
    except Exception as e:
        logger.error(f"获取K线数据失败 {code}: {e}")
        try: bs.logout()
        except: pass
        return None


def get_index_data_for_review():
    data = {"sh": None, "sz": None, "cy": None}
    try:
        ak = _get_akshare()
        df = _safe_fetch(ak.stock_zh_index_daily_em, retries=1)
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            data["sh"] = {
                "close": float(latest.get("close", 0)),
                "change_pct": float((latest.get("close", 0) - prev.get("close", 0)) / prev.get("close", 1) * 100),
                "volume": float(latest.get("volume", 0)),
            }
    except Exception as e:
        logger.error(f"获取指数复盘数据失败: {e}")
    return data
