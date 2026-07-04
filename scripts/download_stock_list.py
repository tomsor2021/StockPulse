# -*- coding: utf-8 -*-
"""下载全A股和H股代码名称到本地数据库"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak
import baostock as bs
from database.db import get_connection, init_database
from datetime import datetime


def download_a_stocks():
    """下载A股代码名称"""
    print("正在下载A股代码名称列表...")
    count = 0

    # 方法1: AKShare stock_info_a_code_name
    try:
        df = ak.stock_info_a_code_name()
        print(f"AKShare获取到 {len(df)} 条A股记录")
        conn = get_connection()
        for _, row in df.iterrows():
            code = str(row["code"]).split(".")[0]
            name = str(row["name"]).strip()
            if len(code) == 6:
                conn.execute(
                    "INSERT OR REPLACE INTO stock_basic (code, name, market, updated_at) VALUES (?, ?, ?, ?)",
                    (code, name, "A股", datetime.now())
                )
                count += 1
        conn.commit()
        print(f"AKShare写入 {count} 条A股记录")
        return count
    except Exception as e:
        print(f"AKShare下载A股失败: {e}")

    # 方法2: BaoStock
    try:
        bs.login()
        today = datetime.now().strftime("%Y-%m-%d")
        rs = bs.query_all_stock(day=today)
        conn = get_connection()
        while rs.next():
            row = rs.get_row_data()
            full_code = row[0]
            name = row[1]
            code = full_code.split(".")[-1]
            if len(code) == 6:
                conn.execute(
                    "INSERT OR REPLACE INTO stock_basic (code, name, market, updated_at) VALUES (?, ?, ?, ?)",
                    (code, name, "A股", datetime.now())
                )
                count += 1
        conn.commit()
        bs.logout()
        print(f"BaoStock写入 {count} 条A股记录")
        return count
    except Exception as e:
        print(f"BaoStock下载A股失败: {e}")

    return count


def download_h_stocks():
    """下载H股代码名称"""
    print("\n正在下载H股代码名称列表...")
    count = 0

    # 方法1: AKShare stock_hk_spot
    try:
        df = ak.stock_hk_spot()
        print(f"AKShare获取到 {len(df)} 条港股记录")
        conn = get_connection()
        for _, row in df.iterrows():
            code = str(row["代码"]).zfill(5)
            name = str(row["中文名称"]).strip()
            conn.execute(
                "INSERT OR REPLACE INTO stock_basic (code, name, market, updated_at) VALUES (?, ?, ?, ?)",
                (code, name, "H股", datetime.now())
            )
            count += 1
        conn.commit()
        print(f"AKShare写入 {count} 条港股记录")
        return count
    except Exception as e:
        print(f"AKShare下载港股失败: {e}")

    return count


def download_funds():
    """下载基金代码名称"""
    print("\n正在下载基金代码名称列表...")
    count = 0
    
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'
    
    try:
        df = ak.fund_fh_em()
        print(f"基金分红获取到 {len(df)} 条记录")
        fund_map = {}
        for _, row in df.iterrows():
            code = str(row["基金代码"]).strip()
            name = str(row["基金简称"]).strip()
            if code and name and len(code) == 6:
                fund_map[code] = name
        
        conn = get_connection()
        new_count = 0
        for code, name in fund_map.items():
            conn.execute(
                "INSERT OR REPLACE INTO stock_basic (code, name, market, updated_at) VALUES (?, ?, ?, ?)",
                (code, name, "基金", datetime.now())
            )
            new_count += 1
        conn.commit()
        count = new_count
        print(f"普通基金写入 {new_count} 条记录")
    except Exception as e:
        print(f"普通基金下载失败: {e}")
    
    try:
        df = ak.fund_etf_category_sina()
        print(f"新浪ETF获取到 {len(df)} 条记录")
        conn = get_connection()
        new_count = 0
        for _, row in df.iterrows():
            full_code = str(row["代码"]).strip()
            code = ''.join([c for c in full_code if c.isdigit()])
            name = str(row["名称"]).strip()
            if code and name and len(code) >= 5:
                conn.execute(
                    "INSERT OR REPLACE INTO stock_basic (code, name, market, updated_at) VALUES (?, ?, ?, ?)",
                    (code, name, "基金", datetime.now())
                )
                new_count += 1
        conn.commit()
        count += new_count
        print(f"ETF基金写入 {new_count} 条记录")
    except Exception as e:
        print(f"ETF基金下载失败: {e}")
    
    return count


def main():
    print("=" * 50)
    print("股票代码名称下载工具")
    print("=" * 50)

    init_database()

    a_count = download_a_stocks()
    h_count = download_h_stocks()
    fund_count = download_funds()

    print("\n" + "=" * 50)
    print(f"下载完成！")
    print(f"  A股: {a_count} 条")
    print(f"  H股: {h_count} 条")
    print(f"  基金: {fund_count} 条")
    print(f"  总计: {a_count + h_count + fund_count} 条")
    print("=" * 50)

    conn = get_connection()
    cur = conn.execute("SELECT market, COUNT(*) FROM stock_basic GROUP BY market")
    for row in cur:
        print(f"  {row[0]}: {row[1]} 条")


if __name__ == "__main__":
    main()
