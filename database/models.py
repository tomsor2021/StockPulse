"""数据访问层 - 每个表的 CRUD 方法"""
import sqlite3
from datetime import date, datetime, timedelta
from typing import Optional, List
from database.db import get_connection


# ── users ──
def create_user(username: str, password_hash: str, nickname: str = None) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO users (username, password_hash, nickname) VALUES (?, ?, ?)",
        (username, password_hash, nickname or username),
    )
    conn.commit()
    return cur.lastrowid


def get_user_by_username(username: str) -> Optional[sqlite3.Row]:
    cur = get_connection().execute("SELECT * FROM users WHERE username = ?", (username,))
    return cur.fetchone()


def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    cur = get_connection().execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cur.fetchone()


def update_user_nickname(user_id: int, nickname: str):
    conn = get_connection()
    conn.execute("UPDATE users SET nickname = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (nickname, user_id))
    conn.commit()


def update_user_password(user_id: int, password_hash: str):
    conn = get_connection()
    conn.execute("UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (password_hash, user_id))
    conn.commit()


def delete_user(user_id: int):
    conn = get_connection()
    for table in ["watchlist_stocks", "transactions", "review_journals", "watchlist_daily",
                  "attachments", "alert_logs", "settings", "todo_items"]:
        conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()


def get_user_count() -> int:
    cur = get_connection().execute("SELECT COUNT(*) FROM users")
    return cur.fetchone()[0]


# ── watchlist_stocks ──
def add_watchlist_stock(user_id: int, code: str, name: str = None, group_name: str = "观察池",
                        note: str = None, alert_up_pct: float = None, alert_down_pct: float = None,
                        alert_volume_ratio: float = None, alert_break_price: float = None) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT OR REPLACE INTO watchlist_stocks (user_id, code, name, group_name, note, alert_up_pct, alert_down_pct, alert_volume_ratio, alert_break_price, is_active) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
        (user_id, code, name, group_name, note, alert_up_pct, alert_down_pct, alert_volume_ratio, alert_break_price),
    )
    conn.commit()
    return cur.lastrowid


def get_watchlist(user_id: int, group_name: str = None) -> List[sqlite3.Row]:
    conn = get_connection()
    if group_name:
        cur = conn.execute(
            "SELECT * FROM watchlist_stocks WHERE user_id = ? AND group_name = ? AND is_active = 1 ORDER BY added_at DESC",
            (user_id, group_name),
        )
    else:
        cur = conn.execute(
            "SELECT * FROM watchlist_stocks WHERE user_id = ? AND is_active = 1 ORDER BY group_name, added_at DESC",
            (user_id,),
        )
    return cur.fetchall()


def get_watchlist_stock(user_id: int, code: str, group_name: str = None) -> Optional[sqlite3.Row]:
    conn = get_connection()
    if group_name:
        cur = conn.execute(
            "SELECT * FROM watchlist_stocks WHERE user_id = ? AND code = ? AND group_name = ? AND is_active = 1", 
            (user_id, code, group_name)
        )
    else:
        cur = conn.execute(
            "SELECT * FROM watchlist_stocks WHERE user_id = ? AND code = ? AND is_active = 1", (user_id, code)
        )
    return cur.fetchone()


def update_watchlist_stock(user_id: int, code: str, group_name: str = None, **kwargs):
    conn = get_connection()
    allowed = {"name", "group_name", "note", "alert_up_pct", "alert_down_pct", "alert_volume_ratio", "alert_break_price"}
    sets = []
    vals = []
    for k, v in kwargs.items():
        if k in allowed:
            sets.append(f"{k} = ?")
            vals.append(v)
    if sets:
        vals.append(user_id)
        vals.append(code)
        where = "WHERE user_id = ? AND code = ?"
        if group_name:
            where += " AND group_name = ?"
            vals.append(group_name)
        conn.execute(f"UPDATE watchlist_stocks SET {', '.join(sets)} {where}", vals)
        conn.commit()


def soft_delete_watchlist_stock(user_id: int, code: str, group_name: str = None):
    conn = get_connection()
    if group_name:
        conn.execute("UPDATE watchlist_stocks SET is_active = 0 WHERE user_id = ? AND code = ? AND group_name = ?", 
                     (user_id, code, group_name))
    else:
        conn.execute("UPDATE watchlist_stocks SET is_active = 0 WHERE user_id = ? AND code = ?", (user_id, code))
    conn.commit()


# ── transactions ──
def add_transaction(user_id: int, trade_date: str, code: str, name: str, direction: str,
                    price: float, quantity: int, fee: float = 0, reason: str = None) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO transactions (user_id, trade_date, code, name, direction, price, quantity, fee, reason) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, trade_date, code, name, direction, price, quantity, fee, reason),
    )
    conn.commit()
    return cur.lastrowid


def get_transactions(user_id: int, start_date: str = None, end_date: str = None,
                     code: str = None, direction: str = None) -> List[sqlite3.Row]:
    conn = get_connection()
    where = ["user_id = ?"]
    vals = [user_id]
    if start_date:
        where.append("trade_date >= ?")
        vals.append(start_date)
    if end_date:
        where.append("trade_date <= ?")
        vals.append(end_date)
    if code:
        where.append("code = ?")
        vals.append(code)
    if direction:
        where.append("direction = ?")
        vals.append(direction)
    cur = conn.execute(
        f"SELECT * FROM transactions WHERE {' AND '.join(where)} ORDER BY trade_date DESC, created_at DESC",
        vals,
    )
    return cur.fetchall()


def delete_transaction(tx_id: int, user_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user_id))
    conn.commit()


def get_recent_buy_price(user_id: int, code: str, before_date: str) -> Optional[float]:
    """获取某只股票在某个日期之前最近一次买入价格"""
    cur = get_connection().execute(
        "SELECT price FROM transactions WHERE user_id = ? AND code = ? AND direction = 'buy' AND trade_date <= ? "
        "ORDER BY trade_date DESC, created_at DESC LIMIT 1",
        (user_id, code, before_date),
    )
    row = cur.fetchone()
    return row["price"] if row else None


def get_monthly_trade_summary(user_id: int, year: int = None) -> List[sqlite3.Row]:
    """获取月度交易统计"""
    if year is None:
        year = datetime.now().year
    conn = get_connection()
    cur = conn.execute("""
        SELECT strftime('%Y-%m', trade_date) as month,
               SUM(CASE WHEN direction='buy' THEN amount ELSE 0 END) as total_buy,
               SUM(CASE WHEN direction='sell' THEN amount ELSE 0 END) as total_sell,
               SUM(fee) as total_fee,
               COUNT(*) as trade_count
        FROM transactions
        WHERE user_id = ? AND strftime('%Y', trade_date) = ?
        GROUP BY month ORDER BY month
    """, (user_id, str(year)))
    return cur.fetchall()


# ── market_snapshots ──
def upsert_market_snapshot(date_str: str, sh_code: str, sh_close: float, sh_change: float, sh_vol: float,
                           sz_code: str, sz_close: float, sz_change: float, sz_vol: float,
                           cy_code: str, cy_close: float, cy_change: float, cy_vol: float,
                           limit_up: int, limit_down: int, total_limit_up: int, sentiment: str):
    conn = get_connection()
    conn.execute("""
        INSERT INTO market_snapshots (date, sh_code, sh_close, sh_change_pct, sh_volume, sz_code, sz_close, sz_change_pct, sz_volume,
                                       cy_code, cy_close, cy_change_pct, cy_volume, limit_up_count, limit_down_count,
                                       total_limit_up, sentiment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            sh_close=excluded.sh_close, sh_change_pct=excluded.sh_change_pct, sh_volume=excluded.sh_volume,
            sz_close=excluded.sz_close, sz_change_pct=excluded.sz_change_pct, sz_volume=excluded.sz_volume,
            cy_close=excluded.cy_close, cy_change_pct=excluded.cy_change_pct, cy_volume=excluded.cy_volume,
            limit_up_count=excluded.limit_up_count, limit_down_count=excluded.limit_down_count,
            total_limit_up=excluded.total_limit_up, sentiment=excluded.sentiment,
            created_at=CURRENT_TIMESTAMP
    """, (date_str, sh_code, sh_close, sh_change, sh_vol, sz_code, sz_close, sz_change, sz_vol,
          cy_code, cy_close, cy_change, cy_vol, limit_up, limit_down, total_limit_up, sentiment))
    conn.commit()


def get_today_market_snapshot(today: str = None) -> Optional[sqlite3.Row]:
    if today is None:
        today = date.today().isoformat()
    cur = get_connection().execute("SELECT * FROM market_snapshots WHERE date = ?", (today,))
    return cur.fetchone()


def get_latest_market_snapshot() -> Optional[sqlite3.Row]:
    cur = get_connection().execute("SELECT * FROM market_snapshots ORDER BY date DESC LIMIT 1")
    return cur.fetchone()


def get_market_snapshots(days: int = 5) -> List[sqlite3.Row]:
    start = (date.today() - timedelta(days=days)).isoformat()
    cur = get_connection().execute(
        "SELECT * FROM market_snapshots WHERE date >= ? ORDER BY date ASC", (start,)
    )
    return cur.fetchall()


# ── review_journals ──
def upsert_review_journal(user_id: int, review_date: str, market_diagnosis: str = None,
                          sector_rotation: str = None, limit_up_analysis: str = None,
                          personal_review: str = None, emotion_score: int = None,
                          discipline_score: int = None, plan_for_tomorrow: str = None):
    conn = get_connection()
    conn.execute("""
        INSERT INTO review_journals (user_id, review_date, market_diagnosis, sector_rotation, limit_up_analysis,
                                      personal_review, emotion_score, discipline_score, plan_for_tomorrow)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, review_date) DO UPDATE SET
            market_diagnosis=excluded.market_diagnosis, sector_rotation=excluded.sector_rotation,
            limit_up_analysis=excluded.limit_up_analysis, personal_review=excluded.personal_review,
            emotion_score=excluded.emotion_score, discipline_score=excluded.discipline_score,
            plan_for_tomorrow=excluded.plan_for_tomorrow, updated_at=CURRENT_TIMESTAMP
    """, (user_id, review_date, market_diagnosis, sector_rotation, limit_up_analysis,
          personal_review, emotion_score, discipline_score, plan_for_tomorrow))
    conn.commit()


def get_review_journal(user_id: int, review_date: str) -> Optional[sqlite3.Row]:
    cur = get_connection().execute(
        "SELECT * FROM review_journals WHERE user_id = ? AND review_date = ?", (user_id, review_date)
    )
    return cur.fetchone()


def get_review_journals(user_id: int, limit_days: int = 30) -> List[sqlite3.Row]:
    start = (date.today() - timedelta(days=limit_days)).isoformat()
    cur = get_connection().execute(
        "SELECT * FROM review_journals WHERE user_id = ? AND review_date >= ? ORDER BY review_date DESC",
        (user_id, start),
    )
    return cur.fetchall()


def get_all_review_dates(user_id: int) -> List[str]:
    cur = get_connection().execute(
        "SELECT review_date FROM review_journals WHERE user_id = ? ORDER BY review_date", (user_id,)
    )
    return [row["review_date"] for row in cur.fetchall()]


def delete_review_journal(journal_id: int, user_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM review_journals WHERE id = ? AND user_id = ?", (journal_id, user_id))
    conn.commit()


# ── watchlist_daily ──
def upsert_watchlist_daily(user_id: int, date_str: str, stock_code: str, stock_name: str = None,
                           close_price: float = None, change_pct: float = None,
                           volume_ratio: float = None, amplitude: float = None, status: str = None):
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO watchlist_daily (user_id, date, stock_code, stock_name, close_price, change_pct,
                                      volume_ratio, amplitude, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, date_str, stock_code, stock_name, close_price, change_pct, volume_ratio, amplitude, status))
    conn.commit()


def get_watchlist_daily(user_id: int, date_str: str) -> List[sqlite3.Row]:
    cur = get_connection().execute(
        "SELECT * FROM watchlist_daily WHERE user_id = ? AND date = ? ORDER BY change_pct DESC",
        (user_id, date_str),
    )
    return cur.fetchall()


def has_today_watchlist_snapshot(user_id: int, date_str: str) -> bool:
    cur = get_connection().execute(
        "SELECT COUNT(*) FROM watchlist_daily WHERE user_id = ? AND date = ?", (user_id, date_str)
    )
    return cur.fetchone()[0] > 0


# ── alerts ──
def add_alert_log(user_id: int, stock_code: str, stock_name: str, alert_type: str, message: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO alert_logs (user_id, stock_code, stock_name, alert_type, message) VALUES (?, ?, ?, ?, ?)",
        (user_id, stock_code, stock_name, alert_type, message),
    )
    conn.commit()


def get_today_alerts(user_id: int, unread_only: bool = True) -> List[sqlite3.Row]:
    today = date.today().isoformat()
    conn = get_connection()
    if unread_only:
        cur = conn.execute(
            "SELECT * FROM alert_logs WHERE user_id = ? AND date(triggered_at) = ? AND is_read = 0 ORDER BY triggered_at DESC",
            (user_id, today),
        )
    else:
        cur = conn.execute(
            "SELECT * FROM alert_logs WHERE user_id = ? AND date(triggered_at) = ? ORDER BY triggered_at DESC",
            (user_id, today),
        )
    return cur.fetchall()


def mark_alert_read(alert_id: int, user_id: int):
    conn = get_connection()
    conn.execute("UPDATE alert_logs SET is_read = 1 WHERE id = ? AND user_id = ?", (alert_id, user_id))
    conn.commit()


# ── todo_items ──
def add_todo(user_id: int, content: str) -> int:
    conn = get_connection()
    cur = conn.execute("INSERT INTO todo_items (user_id, content) VALUES (?, ?)", (user_id, content))
    conn.commit()
    return cur.lastrowid


def get_todos(user_id: int, include_done: bool = False) -> List[sqlite3.Row]:
    conn = get_connection()
    if include_done:
        cur = conn.execute(
            "SELECT * FROM todo_items WHERE user_id = ? ORDER BY is_done ASC, created_at DESC", (user_id,)
        )
    else:
        cur = conn.execute(
            "SELECT * FROM todo_items WHERE user_id = ? AND is_done = 0 ORDER BY created_at DESC", (user_id,)
        )
    return cur.fetchall()


def toggle_todo(todo_id: int, user_id: int):
    conn = get_connection()
    cur = conn.execute("SELECT is_done FROM todo_items WHERE id = ? AND user_id = ?", (todo_id, user_id))
    row = cur.fetchone()
    if row:
        new_val = 0 if row["is_done"] else 1
        done_at = datetime.now().isoformat() if new_val else None
        conn.execute("UPDATE todo_items SET is_done = ?, done_at = ? WHERE id = ? AND user_id = ?",
                     (new_val, done_at, todo_id, user_id))
        conn.commit()


def delete_todo(todo_id: int, user_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM todo_items WHERE id = ? AND user_id = ?", (todo_id, user_id))
    conn.commit()


# ── settings ──
def get_setting(user_id: int, key: str, default: str = None) -> Optional[str]:
    cur = get_connection().execute(
        "SELECT value FROM settings WHERE user_id = ? AND key = ?", (user_id, key)
    )
    row = cur.fetchone()
    return row["value"] if row else default


def set_setting(user_id: int, key: str, value: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO settings (user_id, key, value) VALUES (?, ?, ?) ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value",
        (user_id, key, value),
    )
    conn.commit()


def get_all_settings(user_id: int) -> List[sqlite3.Row]:
    cur = get_connection().execute("SELECT * FROM settings WHERE user_id = ?", (user_id,))
    return cur.fetchall()


# ── system_config ──
def get_system_config(key: str, default: str = None) -> Optional[str]:
    cur = get_connection().execute("SELECT value FROM system_config WHERE key = ?", (key,))
    row = cur.fetchone()
    return row["value"] if row else default


def set_system_config(key: str, value: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO system_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
        (key, value),
    )
    conn.commit()


# ── win rate ──
def calculate_win_rate(user_id: int, days: int = 20) -> float:
    """计算近期胜率"""
    start = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection()
    sells = conn.execute(
        "SELECT * FROM transactions WHERE user_id = ? AND direction = 'sell' AND trade_date >= ? ORDER BY trade_date",
        (user_id, start),
    ).fetchall()
    if not sells:
        return 0.0
    wins = 0
    for sell in sells:
        buy_price = get_recent_buy_price(user_id, sell["code"], sell["trade_date"])
        if buy_price and sell["price"] > buy_price:
            wins += 1
    return round(wins / len(sells) * 100, 1) if sells else 0.0


def calculate_win_rate_detail(user_id: int, days: int = 20) -> dict:
    """计算近期胜率详情，含每日胜率"""
    start = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection()
    sells = conn.execute(
        "SELECT * FROM transactions WHERE user_id = ? AND direction = 'sell' AND trade_date >= ? ORDER BY trade_date",
        (user_id, start),
    ).fetchall()
    if not sells:
        return {"total": 0, "wins": 0, "rate": 0.0, "daily": []}
    wins = 0
    for sell in sells:
        buy_price = get_recent_buy_price(user_id, sell["code"], sell["trade_date"])
        if buy_price and sell["price"] > buy_price:
            wins += 1
    return {"total": len(sells), "wins": wins, "rate": round(wins / len(sells) * 100, 1)}


def get_current_positions(user_id: int) -> list:
    """获取当前持仓（买入-卖出汇总）"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT code, name,
               SUM(CASE WHEN direction='buy' THEN quantity ELSE 0 END) as buy_qty,
               SUM(CASE WHEN direction='sell' THEN quantity ELSE 0 END) as sell_qty,
               SUM(CASE WHEN direction='buy' THEN amount ELSE 0 END) as buy_amt,
               SUM(CASE WHEN direction='sell' THEN amount ELSE 0 END) as sell_amt,
               SUM(fee) as total_fee
        FROM transactions WHERE user_id = ?
        GROUP BY code
        HAVING buy_qty > sell_qty
        ORDER BY (buy_amt - sell_amt) DESC
    """, (user_id,))
    positions = []
    for row in rows.fetchall():
        hold_qty = row["buy_qty"] - row["sell_qty"]
        cost = (row["buy_amt"] - row["sell_amt"]) / hold_qty if hold_qty > 0 else 0
        positions.append({
            "code": row["code"],
            "name": row["name"],
            "hold_qty": hold_qty,
            "cost": round(cost, 2),
            "total_cost": round(row["buy_amt"] - row["sell_amt"], 2),
        })
    return positions


# ── attachments ──
def add_attachment(user_id: int, journal_id: Optional[int], file_path: str, file_name: str, file_type: str, file_size: int) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO attachments (user_id, journal_id, file_path, file_name, file_type, file_size) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, journal_id, file_path, file_name, file_type, file_size),
    )
    conn.commit()
    return cur.lastrowid


def get_attachments_for_journal(journal_id: int) -> List[sqlite3.Row]:
    cur = get_connection().execute(
        "SELECT * FROM attachments WHERE journal_id = ? ORDER BY uploaded_at", (journal_id,)
    )
    return cur.fetchall()
