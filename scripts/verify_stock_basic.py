# -*- coding: utf-8 -*-
"""验证本地股票基础数据"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_connection

conn = get_connection()

# 统计
print("=== 本地股票基础数据统计 ===")
cur = conn.execute("SELECT market, COUNT(*) FROM stock_basic GROUP BY market")
for r in cur:
    print(f"  {r[0]}: {r[1]} 条")

# 抽查
print("\n=== 抽查常见股票 ===")
test_codes = ["600000", "000001", "600519", "300750", "601318", "000858"]
for code in test_codes:
    cur = conn.execute("SELECT code, name, market FROM stock_basic WHERE code = ?", (code,))
    row = cur.fetchone()
    if row:
        print(f"  {row[0]} {row[1]} [{row[2]}]")
    else:
        print(f"  {code} 未找到")
