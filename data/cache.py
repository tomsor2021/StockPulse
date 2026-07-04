"""缓存层：检查本地数据时效性"""
import logging
from datetime import datetime, date
from database import models as db
from config.settings import DATA_STALE_SECONDS

logger = logging.getLogger("stockpulse.cache")

_memory_cache = {}


def get_cached_data(key):
    entry = _memory_cache.get(key)
    if entry:
        if (datetime.now() - entry["timestamp"]).total_seconds() < entry["ttl"]:
            return entry["data"]
        else:
            del _memory_cache[key]
    return None


def set_cached_data(key, data, ttl=300):
    _memory_cache[key] = {
        "data": data,
        "timestamp": datetime.now(),
        "ttl": ttl
    }


def clear_cache():
    _memory_cache.clear()


def get_cache_info():
    info = []
    for key, entry in _memory_cache.items():
        age = (datetime.now() - entry["timestamp"]).total_seconds()
        info.append({
            "key": key,
            "age_seconds": round(age, 1),
            "timestamp": entry["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "ttl": entry["ttl"]
        })
    return info


def get_last_fetch_time():
    if not _memory_cache:
        return None
    latest = max(_memory_cache.values(), key=lambda x: x["timestamp"])
    return latest["timestamp"]


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
