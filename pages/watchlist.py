"""自选股池页面"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database import models as db
from data import sync
from config.settings import WATCHLIST_GROUPS
from utils.helpers import parse_stock_code
from components.kline import kline_chart
from data import fetcher


def render():
    uid = st.session_state["user"]["user_id"]
    st.title("⭐ 自选股池")

    # 分组 Tab
    tabs = st.tabs(WATCHLIST_GROUPS)
    for idx, group in enumerate(WATCHLIST_GROUPS):
        with tabs[idx]:
            _render_group(uid, group)


def _render_group(uid, group_name):
    # 添加自选股
    with st.expander("➕ 添加自选股", expanded=False):
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            code_input = st.text_input("股票代码", placeholder="例如 000001 或 600000", key=f"add_code_{group_name}")
        with c2:
            note_input = st.text_input("备注（选填）", key=f"add_note_{group_name}")
        with c3:
            if st.button("添加", key=f"add_btn_{group_name}"):
                if code_input.strip():
                    code = parse_stock_code(code_input.strip())
                    existing = db.get_watchlist_stock(uid, code)
                    if existing:
                        st.warning("该股票已在自选池中")
                    else:
                        name = sync.sync_user_stock(uid, code)
                        db.add_watchlist_stock(uid, code, name or code, group_name, note_input)
                        st.success(f"已添加 {name or code}")
                        st.rerun()

    # 股票列表
    stocks = db.get_watchlist(uid, group_name)
    if not stocks:
        st.info("该分组暂无自选股")
        return

    rows = []
    for s in stocks:
        rows.append({
            "股票代码": s["code"],
            "名称": s["name"] or "",
            "分组": s["group_name"],
            "备注": s["note"] or "",
            "操作": s["code"],
        })
    df = pd.DataFrame(rows)

    for _, row in df.iterrows():
        code = row["操作"]
        with st.container():
            cols = st.columns([1, 2, 1, 2, 0.8, 0.8, 0.8])
            cols[0].markdown(f"**{code}**")
            cols[1].markdown(row["名称"])
            # 现价和涨跌幅从今日快照获取
            today = date.today().isoformat()
            daily = db.get_watchlist_daily(uid, today)
            spot = None
            for d in daily:
                if d["stock_code"] == code:
                    spot = d
                    break
            if spot:
                change = f"{spot['change_pct']:+.2f}%" if spot["change_pct"] else "--"
                clr = "#D32F2F" if spot["change_pct"] and spot["change_pct"] > 0 else "#2E7D32" if spot["change_pct"] and spot["change_pct"] < 0 else "#9E9E9E"
                cols[2].markdown(f"<span style='color:{clr}'>{change}</span>", unsafe_allow_html=True)
                cols[3].markdown(spot["status"] or "正常")
            else:
                cols[2].markdown("--")
                cols[3].markdown("正常")

            # 编辑备注
            if cols[4].button("✏️", key=f"note_{code}"):
                st.session_state[f"edit_note_{code}"] = True
            if st.session_state.get(f"edit_note_{code}"):
                new_note = st.text_input("编辑备注", value=row["备注"], key=f"note_input_{code}")
                if st.button("保存", key=f"save_note_{code}"):
                    db.update_watchlist_stock(uid, code, note=new_note)
                    st.session_state[f"edit_note_{code}"] = False
                    st.rerun()

            # 提醒设置
            if cols[5].button("🔔", key=f"alert_{code}"):
                st.session_state[f"alert_set_{code}"] = True
            if st.session_state.get(f"alert_set_{code}"):
                stock = db.get_watchlist_stock(uid, code)
                with st.popover("提醒设置"):
                    up = st.number_input("涨停提醒(%)", value=stock["alert_up_pct"] or 9.8, step=0.5, key=f"up_{code}")
                    down = st.number_input("跌停提醒(%)", value=stock["alert_down_pct"] or -9.8, step=0.5, key=f"down_{code}")
                    vol = st.number_input("放量倍数", value=stock["alert_volume_ratio"] or 3.0, step=0.5, key=f"vol_{code}")
                    bp = st.number_input("破位价格", value=stock["alert_break_price"] or 0.0, step=0.01, key=f"bp_{code}")
                    if st.button("保存提醒设置", key=f"save_alert_{code}"):
                        db.update_watchlist_stock(uid, code,
                                                  alert_up_pct=up, alert_down_pct=down,
                                                  alert_volume_ratio=vol, alert_break_price=bp)
                        st.success("保存成功")
                        st.session_state[f"alert_set_{code}"] = False
                        st.rerun()

            # 删除
            if cols[6].button("🗑", key=f"del_{code}"):
                db.soft_delete_watchlist_stock(uid, code)
                st.rerun()

    # 个股详情区（K线）
    st.divider()
    st.subheader("📈 个股K线详情")

    stock_codes = {f"{s['code']} {s['name'] or ''}": s['code'] for s in stocks}
    if stock_codes:
        selected = st.selectbox("选择个股查看", list(stock_codes.keys()), key=f"detail_{group_name}")
        if selected:
            code = stock_codes[selected]
            start = (date.today() - timedelta(days=180)).isoformat()
            kdf = fetcher.fetch_kline_data(code, start)
            if kdf is not None and not kdf.empty:
                fig = kline_chart(kdf)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("K线数据暂不可用")

