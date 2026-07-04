from database.db import get_connection
conn = get_connection()

print('=== 所有表 ===')
cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
for t in tables:
    print(t[0])

print()
print('=== 用户表 ===')
cur = conn.execute('SELECT * FROM users')
users = cur.fetchall()
for u in users:
    print(dict(u))

print()
print('=== 自选股表 watchlist_stocks ===')
try:
    cur = conn.execute('SELECT * FROM watchlist_stocks')
    wl = cur.fetchall()
    for w in wl:
        print(dict(w))
except Exception as e:
    print(f'Error: {e}')

print()
print('=== 市场快照 market_snapshots ===')
try:
    cur = conn.execute('SELECT * FROM market_snapshots')
    ms = cur.fetchall()
    for m in ms:
        print(dict(m))
except Exception as e:
    print(f'Error: {e}')

print()
print('=== 自选股每日数据 watchlist_daily ===')
try:
    cur = conn.execute('SELECT * FROM watchlist_daily')
    wd = cur.fetchall()
    for w in wd:
        print(dict(w))
except Exception as e:
    print(f'Error: {e}')

conn.close()