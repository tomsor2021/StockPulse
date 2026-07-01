"""启动同步逻辑 + 手动刷新入口"""
import logging
from datetime import date
from database import models as db
from data import fetcher
from config.settings import SH_INDEX_CODE, SZ_INDEX_CODE, CY_INDEX_CODE

logger = logging.getLogger("stockpulse.sync")


def sync_all(user_id, progress_callback=None):
    logger.info(f"开始数据同步 (user={user_id})")
    today = date.today().isoformat()
    if progress_callback:
        progress_callback(10, "正在获取大盘行情...")
    _sync_market_snapshot(today)
    if progress_callback:
        progress_callback(40, "正在获取自选股行情...")
    _sync_watchlist_daily(user_id, today)
    if progress_callback:
        progress_callback(70, "正在检查提醒...")
    _check_alerts(user_id, today)
    if progress_callback:
        progress_callback(85, "正在获取涨停板数据...")
    _sync_limit_up(today)
    if progress_callback:
        progress_callback(100, "同步完成")
    logger.info(f"数据同步完成 (user={user_id})")


def _sync_market_snapshot(today):
    market = fetcher.fetch_market_overview()
    if market:
        db.upsert_market_snapshot(
            date_str=today,
            sh_code=SH_INDEX_CODE, sh_change=None, sh_vol=None,
            sz_code=SZ_INDEX_CODE, sz_change=None, sz_vol=None,
            cy_code=CY_INDEX_CODE, cy_change=None, cy_vol=None,
            limit_up=market["limit_up"], limit_down=market["limit_down"],
            total_limit_up=market.get("limit_up", 0), sentiment=None,
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
