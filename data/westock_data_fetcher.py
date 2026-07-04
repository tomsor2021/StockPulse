"""westock-data 数据获取封装"""
import subprocess
import logging
import re
import pandas as pd
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
from data.cache import get_cached_data, set_cached_data

logger = logging.getLogger("stockpulse.westock_data")

_WESTOCK_CMD = ["C:\\Users\\Administrator\\AppData\\Roaming\\npm\\westock-data-skillhub.cmd"]


def _run_westock_command(args, timeout=30):
    try:
        result = subprocess.run(
            _WESTOCK_CMD + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
        )
        if result.returncode != 0:
            logger.warning(f"westock-data 命令失败: {' '.join(args)}, 错误: {result.stderr[:200]}")
            return None
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.warning(f"westock-data 命令超时: {' '.join(args)}")
        return None
    except Exception as e:
        logger.error(f"westock-data 命令执行异常: {e}")
        return None


def _parse_markdown_table(output):
    if not output:
        return None
    
    lines = output.strip().split("\n")
    
    table_start = 0
    for i, line in enumerate(lines):
        if line.startswith("|"):
            table_start = i
            break
    
    if table_start >= len(lines) - 2:
        return None
    
    header_line = lines[table_start].strip()
    data_lines = lines[table_start + 2:]
    
    headers = [h.strip() for h in re.split(r"\|\s*", header_line) if h.strip()]
    
    rows = []
    for line in data_lines:
        line = line.strip()
        if line.startswith("|"):
            row = [cell.strip() for cell in re.split(r"\|\s*", line) if cell.strip()]
            if len(row) == len(headers):
                rows.append(dict(zip(headers, row)))
    
    if rows:
        return rows
    return None


def _convert_code(code):
    if len(code) == 5:
        return f"hk{code}"
    elif len(code) == 6:
        return f"sh{code}" if code.startswith("6") else f"sz{code}"
    return code


def _extract_code(code):
    if code.startswith("sh") or code.startswith("sz"):
        return code[2:]
    elif code.startswith("hk"):
        return code[2:]
    elif code.startswith("us"):
        return code[2:]
    return code


def fetch_quote(codes):
    if isinstance(codes, str):
        codes = [codes]
    
    if not codes:
        return None
    
    cache_key = f"quote_{'_'.join(sorted(codes))}"
    cached = get_cached_data(cache_key)
    if cached:
        return cached
    
    westock_codes = [_convert_code(code) for code in codes]
    codes_str = ",".join(westock_codes)
    
    output = _run_westock_command(["kline", codes_str, "--period", "day", "--limit", "2"])
    if not output:
        return None
    
    data = _parse_markdown_table(output)
    if not data:
        return None
    
    grouped = {}
    for row in data:
        symbol = row.get("symbol", "")
        if symbol not in grouped:
            grouped[symbol] = []
        grouped[symbol].append(row)
    
    results = []
    for symbol, rows in grouped.items():
        if len(rows) < 2:
            continue
        
        code = _extract_code(symbol)
        latest = rows[0]
        prev = rows[1]
        
        latest_price = float(latest.get("last", latest.get("close", 0)))
        prev_price = float(prev.get("last", prev.get("close", 0)))
        
        change_pct = ((latest_price - prev_price) / prev_price * 100) if prev_price > 0 else 0
        
        results.append({
            "代码": code,
            "名称": "",
            "最新价": latest_price,
            "涨跌幅": round(change_pct, 2),
            "量比": None,
            "振幅": None,
            "成交量": float(latest.get("volume", 0)),
            "成交额": float(latest.get("amount", 0)),
            "换手率": None,
            "PE": None,
            "PB": None,
        })
    
    if results:
        set_cached_data(cache_key, results, ttl=120)
    
    return results if results else None


def fetch_stock_name(code):
    westock_code = _convert_code(code)
    output = _run_westock_command(["profile", westock_code])
    if not output:
        return None
    
    data = _parse_markdown_table(output)
    if data:
        return data[0].get("名称", data[0].get("name", None))
    return None


def fetch_stock_names(codes):
    if isinstance(codes, str):
        codes = [codes]
    
    if not codes:
        return {}
    
    name_map = {}
    missing_codes = []
    
    try:
        from database.db import get_connection
        conn = get_connection()
        placeholders = ",".join("?" * len(codes))
        cur = conn.execute(f"SELECT code, name FROM stock_basic WHERE code IN ({placeholders})", tuple(codes))
        for row in cur.fetchall():
            name_map[row[0]] = row[1]
        conn.close()
    except Exception as e:
        logger.warning(f"从数据库获取股票名称缓存失败: {e}")
    
    missing_codes = [code for code in codes if code not in name_map]
    
    if missing_codes:
        westock_codes = [_convert_code(code) for code in missing_codes]
        codes_str = ",".join(westock_codes)
        
        output = _run_westock_command(["profile", codes_str])
        if output:
            data = _parse_markdown_table(output)
            if data:
                for row in data:
                    code = row.get("code", "")
                    name = row.get("名称", row.get("name", ""))
                    code = _extract_code(code)
                    if code and name:
                        name_map[code] = name
                
                try:
                    from database.db import get_connection
                    conn = get_connection()
                    for code in name_map:
                        if code in missing_codes:
                            conn.execute(
                                "INSERT OR REPLACE INTO stock_basic (code, name, market, updated_at) VALUES (?, ?, ?, ?)",
                                (code, name_map[code], "A股" if len(code) == 6 else "港股", date.today())
                            )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.warning(f"保存股票名称缓存失败: {e}")
    
    return name_map


def search_stock(keyword):
    output = _run_westock_command(["search", keyword])
    if not output:
        return None
    
    data = _parse_markdown_table(output)
    if not data:
        return None
    
    results = []
    for item in data:
        code = item.get("代码", item.get("code", ""))
        name = item.get("名称", item.get("name", ""))
        market_type = item.get("市场", item.get("type", ""))
        
        code = _extract_code(code)
        
        market = ""
        if market_type == "GP" or item.get("代码", "").startswith("hk"):
            market = "港股" if len(code) == 5 else "A股"
        elif item.get("代码", "").startswith("us"):
            market = "美股"
        
        results.append({
            "代码": code,
            "名称": name,
            "市场": market,
        })
    
    return results


def fetch_kline(code, start_date, end_date=None, period="day", adjust="qfq"):
    westock_code = _convert_code(code)
    
    args = ["kline", westock_code, "--period", period, "--limit", "500"]
    if adjust:
        args.extend(["--fq", adjust])
    
    output = _run_westock_command(args)
    if not output:
        return None
    
    data = _parse_markdown_table(output)
    if not data:
        return None
    
    rows = []
    for item in data:
        try:
            rows.append({
                "date": item.get("date", ""),
                "open": float(item.get("open", 0)),
                "high": float(item.get("high", 0)),
                "low": float(item.get("low", 0)),
                "close": float(item.get("last", item.get("close", 0))),
                "volume": float(item.get("volume", 0)),
                "amount": float(item.get("amount", 0)),
                "pctChg": float(item.get("exchange", item.get("pctChg", 0))),
            })
        except (ValueError, TypeError):
            continue
    
    if not rows:
        return None
    
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    return df


def fetch_finance(code, num=1):
    westock_code = _convert_code(code)
    
    args = ["finance", westock_code]
    if num > 1:
        args.extend(["--num", str(num)])
    
    output = _run_westock_command(args)
    if not output:
        return None
    
    data = _parse_markdown_table(output)
    return data


def fetch_technical(code, groups="all"):
    westock_code = _convert_code(code)
    
    args = ["technical", westock_code, "--indicator", groups]
    output = _run_westock_command(args)
    if not output:
        return None
    
    data = _parse_markdown_table(output)
    return data


def fetch_sector(keyword):
    output = _run_westock_command(["search", keyword, "--type", "sector"])
    if not output:
        return None
    
    data = _parse_markdown_table(output)
    return data


def fetch_sector_stocks(sector_code):
    output = _run_westock_command(["sector", "constituent", sector_code])
    if not output:
        return None
    
    data = _parse_markdown_table(output)
    if not data:
        return None
    
    results = []
    for item in data:
        code = item.get("代码", item.get("code", ""))
        code = _extract_code(code)
        
        results.append({
            "代码": code,
            "名称": item.get("名称", item.get("name", "")),
            "最新价": float(item.get("最新价", item.get("last", 0))) if item.get("最新价") or item.get("last") else None,
            "涨跌幅": float(item.get("涨跌幅", item.get("exchange", 0))) if item.get("涨跌幅") or item.get("exchange") else None,
        })
    
    return results


def fetch_risk(code):
    if len(code) != 6:
        logger.warning(f"风险事件仅支持A股6位代码")
        return None
    
    westock_code = _convert_code(code)
    output = _run_westock_command(["risk", westock_code])
    if not output:
        return None
    
    data = _parse_markdown_table(output)
    return data


def fetch_index_quote(index_codes):
    if isinstance(index_codes, str):
        index_codes = [index_codes]
    
    if not index_codes:
        return None
    
    cache_key = f"index_{'_'.join(sorted(index_codes))}"
    cached = get_cached_data(cache_key)
    if cached:
        return cached
    
    codes_str = ",".join(index_codes)
    output = _run_westock_command(["kline", codes_str, "--period", "day", "--limit", "2"])
    if not output:
        return None
    
    data = _parse_markdown_table(output)
    if not data:
        return None
    
    grouped = {}
    for row in data:
        symbol = row.get("symbol", "")
        if symbol not in grouped:
            grouped[symbol] = []
        grouped[symbol].append(row)
    
    results = {}
    for symbol, rows in grouped.items():
        if len(rows) < 2:
            continue
        
        latest = rows[0]
        prev = rows[1]
        
        latest_close = float(latest.get("last", latest.get("close", 0)))
        prev_close = float(prev.get("last", prev.get("close", 0)))
        
        change_pct = ((latest_close - prev_close) / prev_close * 100) if prev_close > 0 else 0
        
        results[symbol] = {
            "close": latest_close,
            "change_pct": round(change_pct, 2),
            "volume": float(latest.get("amount", 0)),
        }
    
    if results:
        set_cached_data(cache_key, results, ttl=120)
    
    return results if results else None


def fetch_market_overview():
    cache_key = "market_overview"
    cached = get_cached_data(cache_key)
    if cached:
        return cached
    
    try:
        output = _run_westock_command(["changedist"])
        if output:
            data = _parse_markdown_table(output)
            if data and len(data) > 0:
                item = data[0]
                result = {
                    "total": int(item.get("上涨", 0)) + int(item.get("下跌", 0)) + int(item.get("平盘", 0)),
                    "up": int(item.get("上涨", 0)),
                    "down": int(item.get("下跌", 0)),
                    "limit_up": int(item.get("涨停", 0)),
                    "limit_down": int(item.get("跌停", 0)),
                    "date": str(date.today()),
                }
                set_cached_data(cache_key, result, ttl=120)
                return result
    except Exception as e:
        logger.error(f"westock-data 获取市场总览失败: {e}")
    
    return None


def fetch_limit_up_pool():
    return None


def is_westock_available():
    result = _run_westock_command(["kline", "sh600000", "--period", "day", "--limit", "1"], timeout=30)
    return result is not None