"""缓存层：检查本地数据时效性"""
import logging
from datetime import datetime, date
from database import models as db
from config.settings import DATA_STALE_SECONDS

logger = logging.getLogger("stockpulse.cache")


def is_market_data_stale(user_id):
    today = date.today().isoformat()
    snapshot = db.get_today_market_snapshot(today)
    if not snapshot:
        latest = db.get_latest_market_snapshot()
        if not latest:
            return True
        age = (datetime.now() - datetime.strptime(latest["created_at"][:19], "%Y-%m-%d %H:%M:%S")).total_seconds()
        return age > DATA_STALE_SECONDS
    return False


def need_sync(user_id):
    today = date.today().isoformat()
    return not db.has_today_watchlist_snapshot(user_id, today)
