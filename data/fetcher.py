"""数据获取：westock-data、AKShare 实时行情、Baostock 日K线"""
import logging
import time
import pandas as pd
import streamlit as st
from datetime import date

logger = logging.getLogger("stockpulse.fetcher")
_last_request_time = 0.0

try:
    from data import westock_data_fetcher as wdf
except Exception as e:
    logger.warning(f"westock-data 模块加载失败: {e}")
    wdf = None


def _is_westock_available():
    try:
        if wdf is not None:
            return wdf.is_westock_available()
    except Exception:
        pass
    return False


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
    import os
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'
    import akshare as ak
    return ak


def fetch_market_overview():
    if _is_westock_available():
        try:
            result = wdf.fetch_market_overview()
            if result:
                return result
        except Exception as e:
            logger.warning(f"westock-data 获取市场总览失败: {e}")

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
    if _is_westock_available():
        try:
            result = wdf.fetch_limit_up_pool()
            if result:
                return result
        except Exception as e:
            logger.warning(f"westock-data 获取涨停板数据失败: {e}")
    
    try:
        ak = _get_akshare()
        return _safe_fetch(ak.stock_zt_pool_em, retries=1)
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


@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_spot(codes=None):
    if not codes:
        return None
    
    results = []

    if _is_westock_available():
        try:
            from concurrent.futures import ThreadPoolExecutor
            
            with ThreadPoolExecutor(max_workers=2) as executor:
                quote_future = executor.submit(wdf.fetch_quote, codes)
                names_future = executor.submit(wdf.fetch_stock_names, codes)
                
                westock_results = quote_future.result()
                name_map = names_future.result()
                
            if westock_results:
                for item in westock_results:
                    name = name_map.get(item["代码"], "")
                    results.append({
                        "代码": item["代码"],
                        "名称": name if name else item["名称"],
                        "最新价": item["最新价"],
                        "涨跌幅": item["涨跌幅"],
                        "量比": item["量比"],
                        "振幅": item["振幅"],
                        "成交量": item["成交量"],
                        "成交额": item["成交额"],
                    })
                return pd.DataFrame(results)
        except Exception as e:
            logger.warning(f"westock-data 获取行情失败: {e}")

    a_codes = [c for c in codes if len(c) == 6]
    hk_codes = [c for c in codes if len(c) == 5]

    if a_codes:
        try:
            ak = _get_akshare()
            df = _safe_fetch(ak.stock_zh_a_spot_em, retries=2)
            if df is not None and not df.empty:
                df = df[df["代码"].str[:6].isin(a_codes)]
                for _, row in df.iterrows():
                    code = str(row.get("代码", ""))[:6]
                    results.append({
                        "代码": code,
                        "名称": row.get("名称", ""),
                        "最新价": float(row.get("最新价", 0)) if row.get("最新价") else None,
                        "涨跌幅": float(row.get("涨跌幅", 0)) if row.get("涨跌幅") else None,
                        "量比": float(row.get("量比", 0)) if row.get("量比") else None,
                        "振幅": float(row.get("振幅", 0)) if row.get("振幅") else None,
                    })
        except Exception as e:
            logger.error(f"AKShare获取A股行情失败: {e}")

    if hk_codes:
        try:
            ak = _get_akshare()
            df = _safe_fetch(ak.stock_hk_spot, retries=2)
            if df is not None and not df.empty:
                df = df[df["代码"].isin(hk_codes)]
                for _, row in df.iterrows():
                    code = str(row.get("代码", ""))
                    results.append({
                        "代码": code,
                        "名称": row.get("中文名称", row.get("名称", "")),
                        "最新价": float(row.get("最新价", row.get("close", 0))) if row.get("最新价") or row.get("close") else None,
                        "涨跌幅": float(row.get("涨跌幅", 0)) if row.get("涨跌幅") else None,
                        "量比": None,
                        "振幅": None,
                    })
        except Exception as e:
            logger.error(f"AKShare获取港股行情失败(stock_hk_spot): {e}")

        remaining_hk_after_spot = [c for c in hk_codes if c not in [r["代码"] for r in results]]
        if remaining_hk_after_spot:
            try:
                ak = _get_akshare()
                df = _safe_fetch(ak.stock_hk_spot_em, retries=2)
                if df is not None and not df.empty:
                    df = df[df["代码"].isin(remaining_hk_after_spot)]
                    for _, row in df.iterrows():
                        code = str(row.get("代码", ""))
                        results.append({
                            "代码": code,
                            "名称": row.get("名称", ""),
                            "最新价": float(row.get("最新价", 0)) if row.get("最新价") else None,
                            "涨跌幅": float(row.get("涨跌幅", 0)) if row.get("涨跌幅") else None,
                            "量比": None,
                            "振幅": None,
                        })
            except Exception as e:
                logger.error(f"AKShare获取港股行情失败(stock_hk_spot_em): {e}")

    remaining_a = [c for c in a_codes if c not in [r["代码"] for r in results]]
    if remaining_a:
        try:
            import baostock as bs
            bs.login()

            name_map = {}
            for code in remaining_a:
                bs_code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
                rs = bs.query_stock_basic(code=bs_code)
                if rs.error_code == '0' and rs.next():
                    row = rs.get_row_data()
                    name_map[code] = str(row[1])

            today_str = date.today().isoformat()
            for code in remaining_a:
                bs_code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    fields="date,close,pctChg",
                    start_date=today_str,
                    end_date=today_str,
                    frequency="d", adjustflag="2"
                )
                rows = []
                while rs.next():
                    rows.append(rs.get_row_data())

                if not rows:
                    from datetime import timedelta
                    prev_date = (date.today() - timedelta(days=10)).isoformat()
                    rs = bs.query_history_k_data_plus(
                        bs_code,
                        fields="date,close,pctChg",
                        start_date=prev_date,
                        end_date=today_str,
                        frequency="d", adjustflag="2"
                    )
                    rows = []
                    while rs.next():
                        rows.append(rs.get_row_data())

                if rows:
                    latest = rows[-1]
                    results.append({
                        "代码": code,
                        "名称": name_map.get(code, code),
                        "最新价": float(latest[1]) if latest[1] else None,
                        "涨跌幅": float(latest[2]) if latest[2] else None,
                        "量比": None,
                        "振幅": None,
                    })
            bs.logout()
        except Exception as e:
            logger.error(f"Baostock获取A股行情失败: {e}")

    remaining_hk = [c for c in hk_codes if c not in [r["代码"] for r in results]]
    if remaining_hk:
        try:
            from database.db import get_connection
            conn = get_connection()
            for code in remaining_hk:
                cur = conn.execute(
                    "SELECT close_price, change_pct FROM watchlist_daily WHERE stock_code = ? ORDER BY date DESC LIMIT 1",
                    (code,)
                )
                row = cur.fetchone()
                if row:
                    cur_name = conn.execute("SELECT name FROM stock_basic WHERE code = ?", (code,))
                    name_row = cur_name.fetchone()
                    results.append({
                        "代码": code,
                        "名称": name_row[0] if name_row else code,
                        "最新价": row[0],
                        "涨跌幅": row[1],
                        "量比": None,
                        "振幅": None,
                    })
            conn.close()
        except Exception as e:
            logger.error(f"从数据库获取港股行情失败: {e}")

    if results:
        return pd.DataFrame(results)

    return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock_name(code):
    try:
        from database.db import get_connection
        conn = get_connection()
        cur = conn.execute("SELECT name FROM stock_basic WHERE code = ?", (code,))
        row = cur.fetchone()
        if row:
            return row[0]
    except Exception:
        pass

    if _is_westock_available():
        try:
            name = wdf.fetch_stock_name(code)
            if name:
                try:
                    from database.db import get_connection
                    conn = get_connection()
                    market = "港股" if len(code) == 5 else "A股"
                    conn.execute(
                        "INSERT OR REPLACE INTO stock_basic (code, name, market, updated_at) VALUES (?, ?, ?, ?)",
                        (code, name, market, date.today())
                    )
                    conn.commit()
                except Exception:
                    pass
                return name
        except Exception as e:
            logger.warning(f"westock-data 获取股票名称失败: {e}")

    if len(code) == 5:
        try:
            ak = _get_akshare()
            df = _safe_fetch(ak.stock_hk_spot, retries=1)
            if df is not None and not df.empty:
                stock = df[df["代码"] == code]
                if not stock.empty:
                    name = str(stock.iloc[0]["中文名称"])
                    try:
                        from database.db import get_connection
                        conn = get_connection()
                        conn.execute(
                            "INSERT OR REPLACE INTO stock_basic (code, name, market, updated_at) VALUES (?, ?, ?, ?)",
                            (code, name, "港股", date.today())
                        )
                        conn.commit()
                    except Exception:
                        pass
                    return name
        except Exception:
            pass

    if len(code) == 6:
        try:
            import baostock as bs
            lg = bs.login()
            if lg.error_code != '0':
                bs.logout()
                return None

            bs_code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
            rs = bs.query_stock_basic(code=bs_code)
            if rs.error_code == '0' and rs.next():
                row = rs.get_row_data()
                name = str(row[1])
                bs.logout()
                try:
                    from database.db import get_connection
                    conn = get_connection()
                    conn.execute(
                        "INSERT OR REPLACE INTO stock_basic (code, name, market, updated_at) VALUES (?, ?, ?, ?)",
                        (code, name, "A股", date.today())
                    )
                    conn.commit()
                except Exception:
                    pass
                return name
            bs.logout()
        except Exception:
            pass

    return None


def fetch_kline_data(code, start_date, end_date=None, freq="d"):
    if _is_westock_available():
        try:
            period_map = {"d": "day", "w": "week", "m": "month"}
            period = period_map.get(freq, "day")
            df = wdf.fetch_kline(code, start_date, end_date, period)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            logger.warning(f"westock-data 获取K线数据失败: {e}")

    import baostock as bs
    if end_date is None:
        end_date = date.today().isoformat()
    try:
        bs.login()
        if len(code) == 5:
            bs_code = f"hk.{code.zfill(6)}"
        else:
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
    data = {"sh": None, "sz": None, "cy": None, "kc": None}

    if _is_westock_available():
        try:
            index_codes = ["sh000001", "sz399001", "sz399006", "sh000688"]
            westock_results = wdf.fetch_index_quote(index_codes)
            logger.info(f"westock-data 指数数据结果: {westock_results}")
            if westock_results:
                data["sh"] = westock_results.get("sh000001")
                data["sz"] = westock_results.get("sz399001")
                data["cy"] = westock_results.get("sz399006")
                data["kc"] = westock_results.get("sh000688")
                logger.info(f"转换后的指数数据: {data}")
                return data
        except Exception as e:
            logger.warning(f"westock-data 获取指数数据失败: {e}")

    try:
        ak = _get_akshare()
        index_map = {
            "sh": {"symbol": "sh000001", "name": "上证指数"},
            "sz": {"symbol": "sz399001", "name": "深证成指"},
            "cy": {"symbol": "sz399006", "name": "创业板指"},
            "kc": {"symbol": "sh000688", "name": "科创板指"},
        }
        for key, info in index_map.items():
            df = _safe_fetch(ak.stock_zh_index_daily_em, symbol=info["symbol"], retries=1)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else latest
                data[key] = {
                    "close": float(latest.get("close", 0)),
                    "change_pct": float((latest.get("close", 0) - prev.get("close", 0)) / prev.get("close", 1) * 100),
                    "volume": float(latest.get("amount", 0)),
                }
    except Exception as e:
        logger.error(f"AKShare获取指数复盘数据失败: {e}")

    try:
        import baostock as bs
        bs.login()
        bs_index_map = {
            "sh": "sh.000001",
            "sz": "sz.399001",
            "cy": "sz.399006",
            "kc": "sh.000688",
        }
        today_str = date.today().isoformat()
        for key, bs_code in bs_index_map.items():
            if data[key] is not None:
                continue
            rs = bs.query_history_k_data_plus(
                bs_code,
                fields="date,close,amount,pctChg",
                start_date=today_str,
                end_date=today_str,
                frequency="d", adjustflag="2"
            )
            rows = []
            while rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                from datetime import timedelta
                prev_date = (date.today() - timedelta(days=10)).isoformat()
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    fields="date,close,amount,pctChg",
                    start_date=prev_date,
                    end_date=today_str,
                    frequency="d", adjustflag="2"
                )
                rows = []
                while rs.next():
                    rows.append(rs.get_row_data())
            if rows:
                latest = rows[-1]
                data[key] = {
                    "close": float(latest[1]) if latest[1] else None,
                    "change_pct": float(latest[3]) if latest[3] else None,
                    "volume": float(latest[2]) if latest[2] else None,
                }
        bs.logout()
    except Exception as e:
        logger.error(f"Baostock获取指数复盘数据失败: {e}")

    return data


def get_global_index_data():
    data = {"hsi": None, "nikkei": None, "sp500": None, "nasdaq": None}

    if _is_westock_available():
        try:
            index_codes = ["hkHSI", "usIXIC", "usSPX"]
            westock_results = wdf.fetch_index_quote(index_codes)
            if westock_results:
                data["hsi"] = westock_results.get("hkHSI")
                data["nasdaq"] = westock_results.get("usIXIC")
                data["sp500"] = westock_results.get("usSPX")
                return data
        except Exception as e:
            logger.warning(f"westock-data 获取全球指数数据失败: {e}")

    try:
        ak = _get_akshare()

        df = _safe_fetch(ak.index_global_hist_em, symbol="恒生指数", retries=1)
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            data["hsi"] = {
                "close": float(latest.get("最新价", 0)),
                "change_pct": float((latest.get("最新价", 0) - prev.get("最新价", 0)) / prev.get("最新价", 1) * 100),
            }

        df = _safe_fetch(ak.index_global_hist_em, symbol="日经225", retries=1)
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            data["nikkei"] = {
                "close": float(latest.get("最新价", 0)),
                "change_pct": float((latest.get("最新价", 0) - prev.get("最新价", 0)) / prev.get("最新价", 1) * 100),
            }

        df = _safe_fetch(ak.index_global_hist_em, symbol="纳斯达克", retries=1)
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            data["nasdaq"] = {
                "close": float(latest.get("最新价", 0)),
                "change_pct": float((latest.get("最新价", 0) - prev.get("最新价", 0)) / prev.get("最新价", 1) * 100),
            }

        df = _safe_fetch(ak.index_us_stock_sina, retries=1)
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            data["sp500"] = {
                "close": float(latest.get("close", 0)),
                "change_pct": float((latest.get("close", 0) - prev.get("close", 0)) / prev.get("close", 1) * 100),
            }

    except Exception as e:
        logger.error(f"获取全球指数数据失败: {e}")
    return data


def search_stock(keyword):
    if _is_westock_available():
        try:
            results = wdf.search_stock(keyword)
            if results:
                return results
        except Exception as e:
            logger.warning(f"westock-data 搜索股票失败: {e}")
    return None


def fetch_technical_indicators(code, indicators="all"):
    if _is_westock_available():
        try:
            results = wdf.fetch_technical(code, indicators)
            if results:
                return results
        except Exception as e:
            logger.warning(f"westock-data 获取技术指标失败: {e}")
    return None


def fetch_sector_stocks(sector_code):
    if _is_westock_available():
        try:
            results = wdf.fetch_sector_stocks(sector_code)
            if results:
                return results
        except Exception as e:
            logger.warning(f"westock-data 获取板块成份股失败: {e}")
    return None


def fetch_risk_events(code):
    if _is_westock_available():
        try:
            results = wdf.fetch_risk(code)
            if results:
                return results
        except Exception as e:
            logger.warning(f"westock-data 获取风险事件失败: {e}")
    return None


def fetch_finance_data(code, num=1):
    if _is_westock_available():
        try:
            results = wdf.fetch_finance(code, num)
            if results:
                return results
        except Exception as e:
            logger.warning(f"westock-data 获取财务数据失败: {e}")
    return None