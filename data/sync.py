"""启动同步逻辑 + 手动刷新入口"""
import logging
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from database import models as db
from data import fetcher, cache
from config.settings import SH_INDEX_CODE, SZ_INDEX_CODE, CY_INDEX_CODE

logger = logging.getLogger("stockpulse.sync")


def sync_all(user_id, progress_callback=None):
    logger.info(f"开始数据同步 (user={user_id})")
    today = date.today().isoformat()
    
    if progress_callback:
        progress_callback(10, "正在获取数据...")
    
    stocks = db.get_watchlist(user_id)
    codes = [s["code"] for s in stocks] if stocks else []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        market_future = executor.submit(fetcher.fetch_market_overview)
        index_future = executor.submit(fetcher.get_index_data_for_review)
        watchlist_future = executor.submit(fetcher.fetch_stock_spot, codes) if codes else None
        limit_up_future = executor.submit(fetcher.fetch_limit_up_pool)
        global_index_future = executor.submit(fetcher.get_global_index_data)
        
        market = market_future.result()
        index_data = index_future.result()
        spot_df = watchlist_future.result() if watchlist_future else None
        limit_up_future.result()
        global_index_future.result()
    
    if market or any(v is not None for v in index_data.values()):
        db.upsert_market_snapshot(
            date_str=today,
            sh_code=SH_INDEX_CODE,
            sh_close=index_data["sh"]["close"] if index_data["sh"] else None,
            sh_change=index_data["sh"]["change_pct"] if index_data["sh"] else None,
            sh_vol=index_data["sh"]["volume"] if index_data["sh"] else None,
            sz_code=SZ_INDEX_CODE,
            sz_close=index_data["sz"]["close"] if index_data["sz"] else None,
            sz_change=index_data["sz"]["change_pct"] if index_data["sz"] else None,
            sz_vol=index_data["sz"]["volume"] if index_data["sz"] else None,
            cy_code=CY_INDEX_CODE,
            cy_close=index_data["cy"]["close"] if index_data["cy"] else None,
            cy_change=index_data["cy"]["change_pct"] if index_data["cy"] else None,
            cy_vol=index_data["cy"]["volume"] if index_data["cy"] else None,
            limit_up=market["limit_up"] if market else 0, 
            limit_down=market["limit_down"] if market else 0,
            total_limit_up=market.get("limit_up", 0) if market else 0, 
            sentiment=None,
        )
    
    if spot_df is not None and not spot_df.empty:
        for _, row in spot_df.iterrows():
            code = str(row.get("代码", ""))[:6]
            db.upsert_watchlist_daily(
                user_id=user_id, date_str=today,
                stock_code=code, stock_name=row.get("名称", ""),
                close_price=float(row.get("最新价", 0)) if row.get("最新价") else None,
                change_pct=float(row.get("涨跌幅", 0)) if row.get("涨跌幅") else None,
                volume_ratio=float(row.get("量比", 0)) if row.get("量比") else None,
                amplitude=float(row.get("振幅", 0)) if row.get("振幅") else None,
                status="涨停" if row.get("涨跌幅") and float(row["涨跌幅"]) >= 9.8 else (
                    "跌停" if row.get("涨跌幅") and float(row["涨跌幅"]) <= -9.8 else "正常"),
            )
    
    if progress_callback:
        progress_callback(70, "正在检查提醒...")
    _check_alerts(user_id, today)
    
    if progress_callback:
        progress_callback(100, "同步完成")
    
    cache.clear_cache()
    logger.info(f"数据同步完成 (user={user_id})")


def _fetch_market_data():
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            market_future = executor.submit(fetcher.fetch_market_overview)
            index_future = executor.submit(fetcher.get_index_data_for_review)
            
            market = market_future.result()
            index_data = index_future.result()
        
        return {"market": market, "index_data": index_data}
    except Exception as e:
        logger.error(f"获取市场数据失败: {e}")
        return {"market": None, "index_data": {"sh": None, "sz": None, "cy": None, "kc": None}}


def _fetch_limit_up_data(today):
    try:
        pool = fetcher.fetch_limit_up_pool()
        return pool
    except Exception as e:
        logger.error(f"获取涨停板数据失败: {e}")
        return None


def _sync_market_snapshot(today):
    market = fetcher.fetch_market_overview()
    index_data = fetcher.get_index_data_for_review()
    
    has_data = market is not None or any(v is not None for v in index_data.values())
    if has_data:
        db.upsert_market_snapshot(
            date_str=today,
            sh_code=SH_INDEX_CODE,
            sh_close=index_data["sh"]["close"] if index_data["sh"] else None,
            sh_change=index_data["sh"]["change_pct"] if index_data["sh"] else None,
            sh_vol=index_data["sh"]["volume"] if index_data["sh"] else None,
            sz_code=SZ_INDEX_CODE,
            sz_close=index_data["sz"]["close"] if index_data["sz"] else None,
            sz_change=index_data["sz"]["change_pct"] if index_data["sz"] else None,
            sz_vol=index_data["sz"]["volume"] if index_data["sz"] else None,
            cy_code=CY_INDEX_CODE,
            cy_close=index_data["cy"]["close"] if index_data["cy"] else None,
            cy_change=index_data["cy"]["change_pct"] if index_data["cy"] else None,
            cy_vol=index_data["cy"]["volume"] if index_data["cy"] else None,
            limit_up=market["limit_up"] if market else 0, 
            limit_down=market["limit_down"] if market else 0,
            total_limit_up=market.get("limit_up", 0) if market else 0, 
            sentiment=None,
        )


def _sync_watchlist_daily(user_id, today):
    stocks = db.get_watchlist(user_id)
    if not stocks:
        return
    codes = [s["code"] for s in stocks]
    spot_df = fetcher.fetch_stock_spot(codes)
    if spot_df is None:
        return
    for _, row in spot_df.iterrows():
        code = str(row.get("代码", ""))[:6]
        db.upsert_watchlist_daily(
            user_id=user_id, date_str=today,
            stock_code=code, stock_name=row.get("名称", ""),
            close_price=float(row.get("最新价", 0)) if row.get("最新价") else None,
            change_pct=float(row.get("涨跌幅", 0)) if row.get("涨跌幅") else None,
            volume_ratio=float(row.get("量比", 0)) if row.get("量比") else None,
            amplitude=float(row.get("振幅", 0)) if row.get("振幅") else None,
            status="涨停" if row.get("涨跌幅") and float(row["涨跌幅"]) >= 9.8 else (
                "跌停" if row.get("涨跌幅") and float(row["涨跌幅"]) <= -9.8 else "正常"),
        )


def _check_alerts(user_id, today):
    daily_rows = db.get_watchlist_daily(user_id, today)
    for row in daily_rows:
        stock = db.get_watchlist_stock(user_id, row["stock_code"])
        if not stock:
            continue
        change = row["change_pct"]
        if change is None:
            continue
        if stock["alert_up_pct"] and change >= stock["alert_up_pct"]:
            db.add_alert_log(user_id, row["stock_code"], row["stock_name"],
                             "up_limit", f"{row['stock_name']} 涨幅 {change:.2f}%")
        if stock["alert_down_pct"] and change <= stock["alert_down_pct"]:
            db.add_alert_log(user_id, row["stock_code"], row["stock_name"],
                             "down_limit", f"{row['stock_name']} 跌幅 {change:.2f}%")


def _sync_limit_up(today):
    pool = fetcher.fetch_limit_up_pool()
    if pool is not None:
        pass


def sync_user_stock(user_id, code):
    return fetcher.fetch_stock_name(code)
