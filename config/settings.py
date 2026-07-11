"""全局常量、路径、默认值"""
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

if os.environ.get("TENCENT_CLOUDBASE") == "true":
    DB_PATH = Path("/tmp") / "StockPulse.db"
    LOG_DIR = Path("/tmp") / "logs"
    ATTACHMENTS_DIR = Path("/tmp") / "attachments"
else:
    DB_DIR = ROOT_DIR
    DB_PATH = DB_DIR / "StockPulse.db"
    LOG_DIR = ROOT_DIR / "logs"
    ATTACHMENTS_DIR = ROOT_DIR / "attachments"

DB_VERSION = 2
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_LEVEL = "INFO"
LOG_RETENTION_DAYS = 30
DATA_STALE_SECONDS = 300
AKSHARE_REQ_INTERVAL = 0.5
AKSHARE_RETRIES = 2
AKSHARE_TIMEOUT = 10
BAOSTOCK_MAX_DAILY = 50000
DATA_SOURCE_AKSHARE = "AKShare"
DATA_SOURCE_BAOSTOCK = "Baostock"
WATCHLIST_GROUPS = ["短线池", "中线池", "观察池"]
SH_INDEX_CODE = "000001"
SZ_INDEX_CODE = "399001"
CY_INDEX_CODE = "399006"
DEFAULT_ALERT_UP_PCT = 9.8
DEFAULT_ALERT_DOWN_PCT = -9.8
DEFAULT_ALERT_VOLUME_RATIO = 3.0
THEME_LIGHT = "浅色"
THEME_DARK = "深色"
THEME_SYSTEM = "跟随系统"
COLOR_UP = "#D32F2F"
COLOR_DOWN = "#2E7D32"
COLOR_FLAT = "#9E9E9E"
ASSETS_DIR = ROOT_DIR / "assets"
CSS_PATH = ASSETS_DIR / "css" / "custom.css"
LOGO_PATH = ASSETS_DIR / "images" / "logo.png"
ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
MAX_ATTACHMENT_SIZE_MB = 10
ALLOWED_ATTACHMENT_TYPES = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}
