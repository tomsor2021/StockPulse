"""数据库连接管理"""
import sqlite3
import threading
from pathlib import Path
from config.settings import DB_PATH

_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """获取当前线程的数据库连接（单例）"""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return conn


def init_database():
    """初始化所有表结构"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nickname TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS IX_users_username ON users(username);

    CREATE TABLE IF NOT EXISTS watchlist_stocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        code TEXT NOT NULL,
        name TEXT,
        group_name TEXT NOT NULL DEFAULT '观察池',
        note TEXT,
        alert_up_pct REAL,
        alert_down_pct REAL,
        alert_volume_ratio REAL,
        alert_break_price REAL,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1,
        UNIQUE(user_id, code)
    );
    CREATE INDEX IF NOT EXISTS IX_watchlist_user ON watchlist_stocks(user_id, group_name);

    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        trade_date DATE NOT NULL,
        code TEXT NOT NULL,
        name TEXT,
        direction TEXT NOT NULL CHECK(direction IN ('buy','sell')),
        price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        amount REAL GENERATED ALWAYS AS (price * quantity) STORED,
        fee REAL DEFAULT 0,
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS IX_trades_date ON transactions(user_id, trade_date);
    CREATE INDEX IF NOT EXISTS IX_trades_code ON transactions(user_id, code);

    CREATE TABLE IF NOT EXISTS market_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE UNIQUE NOT NULL,
        sh_code TEXT NOT NULL,
        sh_change_pct REAL,
        sh_volume REAL,
        sz_code TEXT NOT NULL,
        sz_change_pct REAL,
        sz_volume REAL,
        cy_code TEXT NOT NULL,
        cy_change_pct REAL,
        cy_volume REAL,
        limit_up_count INTEGER,
        limit_down_count INTEGER,
        total_limit_up INTEGER,
        sentiment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS IX_market_date ON market_snapshots(date);

    CREATE TABLE IF NOT EXISTS review_journals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        review_date DATE NOT NULL,
        market_diagnosis TEXT,
        sector_rotation TEXT,
        limit_up_analysis TEXT,
        personal_review TEXT,
        emotion_score INTEGER CHECK(emotion_score BETWEEN 1 AND 10),
        discipline_score INTEGER CHECK(discipline_score BETWEEN 1 AND 10),
        plan_for_tomorrow TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, review_date)
    );
    CREATE INDEX IF NOT EXISTS IX_journal_date ON review_journals(user_id, review_date);

    CREATE TABLE IF NOT EXISTS watchlist_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        date DATE NOT NULL,
        stock_code TEXT NOT NULL,
        stock_name TEXT,
        close_price REAL,
        change_pct REAL,
        volume_ratio REAL,
        amplitude REAL,
        status TEXT,
        note TEXT
    );
    CREATE INDEX IF NOT EXISTS IX_watchlist_daily ON watchlist_daily(user_id, date);

    CREATE TABLE IF NOT EXISTS attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        journal_id INTEGER REFERENCES review_journals(id),
        file_path TEXT NOT NULL,
        file_name TEXT,
        file_type TEXT,
        file_size INTEGER,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS alert_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        stock_code TEXT NOT NULL,
        stock_name TEXT,
        alert_type TEXT NOT NULL CHECK(alert_type IN ('up_limit','down_limit','volume_spike','price_break','custom')),
        message TEXT,
        is_read INTEGER DEFAULT 0,
        triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS settings (
        user_id INTEGER NOT NULL REFERENCES users(id),
        key TEXT NOT NULL,
        value TEXT,
        PRIMARY KEY (user_id, key)
    );

    CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS todo_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        content TEXT NOT NULL,
        is_done INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        done_at TIMESTAMP
    );
    """)
    conn.commit()

    # 初始化默认系统配置
    _init_default_config(conn)


def _init_default_config(conn):
    defaults = {
        "db_version": "1",
        "data_source": "AKShare",
        "theme": "浅色",
    }
    for key, value in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO system_config (key, value) VALUES (?, ?)",
            (key, value),
        )
    conn.commit()
