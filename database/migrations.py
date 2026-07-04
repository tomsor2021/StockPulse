"""数据库迁移管理"""
import logging
from database.db import get_connection
from config.settings import DB_VERSION

logger = logging.getLogger("stockpulse.migrations")


def get_current_version() -> int:
    """获取当前数据库版本"""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT value FROM system_config WHERE key = 'db_version'")
        row = cur.fetchone()
        return int(row["value"]) if row else 0
    except Exception:
        return 0


def set_version(version: int):
    conn = get_connection()
    conn.execute(
        "INSERT INTO system_config (key, value) VALUES ('db_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP",
        (str(version),),
    )
    conn.commit()


def run_migrations():
    """执行所有待执行的迁移"""
    current = get_current_version()
    target = DB_VERSION
    if current >= target:
        return
    logger.info(f"数据库迁移: {current} → {target}")
    _run_v1_to_current(current)
    set_version(target)
    logger.info("数据库迁移完成")


def _run_v1_to_current(current: int):
    """从当前版本迁移到最新版本"""
    conn = get_connection()
    # v1: 初始版本，表结构由 db.py 的 init_database 创建
    if current < 1:
        logger.info("迁移 v1 已完成（建表由 db.py 处理）")
    # v2: 添加指数收盘价字段
    if current < 2:
        logger.info("迁移 v2: 添加 sh_close, sz_close, cy_close 字段")
        try:
            conn.execute("ALTER TABLE market_snapshots ADD COLUMN sh_close REAL")
            conn.execute("ALTER TABLE market_snapshots ADD COLUMN sz_close REAL")
            conn.execute("ALTER TABLE market_snapshots ADD COLUMN cy_close REAL")
            logger.info("迁移 v2 完成")
        except Exception as e:
            logger.warning(f"迁移 v2 可能已执行: {e}")
    conn.commit()
