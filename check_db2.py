import sqlite3

conn = sqlite3.connect('StockPulse.db')

# 查看 stock_basic 表中02701和06869
cur = conn.execute("SELECT * FROM stock_basic WHERE code IN ('02701', '06869', '00700')")
rows = cur.fetchall()
print("特定港股记录:")
for row in rows:
    print(row)

conn.close()
