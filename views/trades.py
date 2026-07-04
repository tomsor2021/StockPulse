"""交易记录页面"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database import models as db
from utils.helpers import parse_stock_code
from data import fetcher


def render():
    uid = st.session_state["user"]["user_id"]
    st.title("💰 交易记录")

    # 筛选栏
    st.subheader("🔍 筛选")
    c1, c2, c3, c4 = st.columns([2, 2, 1.5, 1.5])
    today = date.today()
    month_start = today.replace(day=1)
    with c1:
        start_date = st.date_input("开始日期", value=month_start, key="trade_start")
    with c2:
        end_date = st.date_input("结束日期", value=today, key="trade_end")
    with c3:
        code_filter = st.text_input("股票代码/名称", key="trade_code_filter")
    with c4:
        dir_filter = st.selectbox("方向", ["全部", "买入", "卖出"], key="trade_dir")
        dir_map = {"全部": None, "买入": "buy", "卖出": "sell"}
        direction = dir_map[dir_filter]

    # 新增交易
    with st.expander("➕ 新增交易", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            t_date = st.date_input("交易日期", value=today, key="new_trade_date")
            t_code = st.text_input("股票代码", placeholder="例如 A股 000001 / 港股 06869", key="new_trade_code")
            
            # 实时查询股票名称（支持A股6位和港股5位）
            trade_stock_name = None
            if t_code.strip():
                code = parse_stock_code(t_code.strip())
                if len(code) in (5, 6):
                    try:
                        trade_stock_name = fetcher.fetch_stock_name(code)
                    except Exception:
                        pass
            
            # 显示股票名称
            if trade_stock_name:
                st.markdown(f"<span style='color:#4CAF50; font-weight:500'>📌 {trade_stock_name}</span>", unsafe_allow_html=True)
            elif t_code.strip() and len(parse_stock_code(t_code.strip())) in (5, 6):
                st.markdown("<span style='color:#FF9800'>⏳ 查询中...</span>", unsafe_allow_html=True)
            
            t_dir = st.selectbox("方向", ["买入", "卖出"], key="new_trade_dir")
            t_price = st.number_input("成交价", step=0.01, format="%.2f", key="new_trade_price")
        with c2:
            t_qty = st.number_input("数量（股）", step=100, min_value=0, key="new_trade_qty")
            t_fee = st.number_input("手续费", step=0.01, format="%.2f", value=0.0, key="new_trade_fee")
            t_reason = st.text_area("买卖理由", key="new_trade_reason", height=80)

        if st.button("保存交易", type="primary", key="save_trade"):
            if t_code.strip() and t_price > 0 and t_qty > 0:
                code = parse_stock_code(t_code.strip())
                if len(code) not in (5, 6):
                    st.error("股票代码必须是5位（港股）或6位（A股）数字")
                    return
                name = trade_stock_name or fetcher.fetch_stock_name(code) or code
                db.add_transaction(uid, t_date.isoformat(), code, name,
                                   "buy" if t_dir == "买入" else "sell",
                                   t_price, int(t_qty), t_fee, t_reason)
                st.success(f"交易记录已保存: {name}")
                st.rerun()
            else:
                st.error("请填写完整的交易信息")

    # 查询交易
    start = start_date.isoformat()
    end = end_date.isoformat()
    code_filter_clean = parse_stock_code(code_filter.strip()) if code_filter.strip() else None

    transactions = db.get_transactions(uid, start, end, code_filter_clean, direction)

    # 表格
    if transactions:
        rows = []
        for t in transactions:
            rows.append({
                "日期": t["trade_date"],
                "代码": t["code"],
                "名称": t["name"] or "",
                "方向": "⬆ 买入" if t["direction"] == "buy" else "⬇ 卖出",
                "成交价": t["price"],
                "数量": t["quantity"],
                "成交额": t["amount"],
                "手续费": t["fee"] or 0,
                "买卖理由": t["reason"] or "",
                "ID": t["id"],
            })
        df = pd.DataFrame(rows)
        df = df[["ID", "日期", "代码", "名称", "方向", "成交价", "数量", "成交额", "手续费", "买卖理由"]]
        st.dataframe(
            df,
            column_config={
                "ID": st.column_config.NumberColumn("ID", width="small"),
                "日期": st.column_config.DateColumn("日期"),
                "成交价": st.column_config.NumberColumn("成交价", format="¥%.2f"),
                "成交额": st.column_config.NumberColumn("成交额", format="¥%.2f"),
                "手续费": st.column_config.NumberColumn("手续费", format="¥%.2f"),
            },
            hide_index=True, width="stretch",
        )

        # 删除交易
        with st.expander("🗑 删除交易"):
            del_id = int(st.number_input("输入要删除的交易 ID", min_value=1, step=1, key="del_trade_id"))
            if st.button("确认删除", type="primary"):
                if del_id > 0:
                    all_tx = db.get_transactions(uid)
                    tx_dict_list = [dict(t) for t in all_tx]
                    if any(t["id"] == del_id for t in tx_dict_list):
                        db.delete_transaction(del_id, uid)
                        st.success("已删除")
                        st.rerun()
                    else:
                        st.error(f"未找到 ID 为 {del_id} 的交易记录")
                else:
                    st.error("请输入有效的交易 ID")

        # 统计
        st.divider()
        st.subheader("📊 交易统计")
        total_buy = sum(t["amount"] for t in transactions if t["direction"] == "buy")
        total_sell = sum(t["amount"] for t in transactions if t["direction"] == "sell")
        total_fee = sum(t["fee"] or 0 for t in transactions)
        trade_count = len(transactions)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("总买入", f"¥{total_buy:,.2f}")
        with c2:
            st.metric("总卖出", f"¥{total_sell:,.2f}")
        with c3:
            st.metric("总手续费", f"¥{total_fee:,.2f}")
        with c4:
            st.metric("交易次数", trade_count)

        # 胜率
        from database.models import calculate_win_rate
        win_rate = calculate_win_rate(uid, 20)
        st.metric("近20个交易日胜率", f"{win_rate}%",
                  delta=f"{'↑' if win_rate >= 50 else '↓'}")

        # 月度盈亏统计
        st.subheader("📅 月度盈亏")
        monthly = db.get_monthly_trade_summary(uid, today.year)
        if monthly:
            import plotly.graph_objects as go
            m_rows = []
            for m in monthly:
                profit = (m["total_sell"] or 0) - (m["total_buy"] or 0) - (m["total_fee"] or 0)
                m_rows.append({"月份": m["month"], "盈亏": round(profit, 2)})
            mdf = pd.DataFrame(m_rows)
            colors = ["#D32F2F" if v >= 0 else "#2E7D32" for v in mdf["盈亏"]]
            fig = go.Figure(data=[go.Bar(x=mdf["月份"], y=mdf["盈亏"], marker_color=colors)])
            fig.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20),
                              yaxis_title="盈亏（元）")
            st.plotly_chart(fig, width="stretch")
    else:
        st.info("暂无交易记录")

