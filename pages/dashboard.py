"""首页看板"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database import models as db
from data import sync, cache
from config.theme import get_theme_color, color_change, arrow_change
from config.settings import THEME_LIGHT
from utils.helpers import format_pct, format_money, today_str
from components.cards import market_index_card, stat_card, alert_item

def render():
    colors = get_theme_color(THEME_LIGHT)
    uid = st.session_state["user"]["user_id"]
    today = today_str()
    user_data = st.session_state["user"]
    display_name = user_data.get('nickname') or user_data.get('username', '用户')

    st.title("首页看板")
    st.caption(f"欢迎回来，{display_name}")

    # 数据刷新
    col_refresh, col_status = st.columns([1, 3])
    with col_refresh:
        if st.button("刷新数据"):
            progress_bar = st.progress(0, text="正在同步...")
            status_text = st.empty()
            def progress_cb(pct, msg):
                progress_bar.progress(pct, text=msg)
            sync.sync_all(uid, progress_callback=progress_cb)
            status_text.success("数据已更新")
            st.rerun()

    # 大盘状态 + 统计
    snapshot = db.get_today_market_snapshot(today)
    if not snapshot:
        snapshot = db.get_latest_market_snapshot()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        market_index_card("上证指数", snapshot["sh_change_pct"] if snapshot else None,
                          snapshot["sh_change_pct"] if snapshot else None,
                          snapshot["sh_volume"] if snapshot else None, colors)
    with c2:
        market_index_card("深证成指", snapshot["sz_change_pct"] if snapshot else None,
                          snapshot["sz_change_pct"] if snapshot else None,
                          snapshot["sz_volume"] if snapshot else None, colors)
    with c3:
        stat_card("涨停", snapshot["limit_up_count"] if snapshot else 0, "家")
    with c4:
        stat_card("跌停", snapshot["limit_down_count"] if snapshot else 0, "家")

    # 今日盈亏 + 持仓占比 + 胜率 + 待办
    c_left, c_right = st.columns([3, 2])

    with c_left:
        st.subheader("近期胜率")
        from database.models import calculate_win_rate_detail
        wr = calculate_win_rate_detail(uid, 20)
        st.metric("胜率", f"{wr['rate']}%", f"{wr['wins']}/{wr['total']}")

        positions = db.get_current_positions(uid)
        if positions:
            st.subheader("当前持仓")
            pos_df = pd.DataFrame(positions)
            st.dataframe(pos_df[["code", "name", "hold_qty", "cost", "total_cost"]],
                         column_config={"code": "代码", "name": "名称", "hold_qty": "持股数",
                                        "cost": "成本价", "total_cost": st.column_config.NumberColumn("总成本", format="%.2f")},
                         hide_index=True, use_container_width=True)

    with c_right:
        st.subheader("待办事项")
        todos = db.get_todos(uid)
        for todo in todos:
            c = st.columns([4, 1])
            with c[0]:
                st.checkbox(todo["content"], key=f"todo_{todo['id']}",
                            on_change=lambda tid=todo['id']: db.toggle_todo(tid, uid))
            with c[1]:
                if st.button("删除", key=f"del_todo_{todo['id']}"):
                    db.delete_todo(todo["id"], uid)
                    st.rerun()
        new_todo = st.text_input("添加待办", placeholder="输入待办事项...", key="new_todo_input")
        if st.button("添加", key="add_todo_btn"):
            if new_todo.strip():
                db.add_todo(uid, new_todo.strip())
                st.rerun()

    # 今日提醒
    st.subheader("今日提醒")
    alerts = db.get_today_alerts(uid)
    if alerts:
        for alert in alerts:
            alert_item(alert["stock_name"] or alert["stock_code"], alert["alert_type"],
                       alert["message"], alert["id"], uid, lambda aid, uid: db.mark_alert_read(aid, uid))
    else:
        st.info("暂无今日提醒")

    # 持仓占比饼图
    if positions:
        st.subheader("持仓占比")
        import plotly.graph_objects as go
        labels = [p["name"] or p["code"] for p in positions[:8]]
        values = [p["total_cost"] for p in positions[:8]]
        if len(positions) > 8:
            labels.append("其他")
            values.append(sum(p["total_cost"] for p in positions[8:]))
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无持仓数据")