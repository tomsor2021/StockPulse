"""每日复盘页面"""
import streamlit as st
from datetime import date
from database import models as db
from config.theme import get_theme_color
from config.settings import THEME_LIGHT
from utils.helpers import today_str, make_sentience_label
from components.kline import kline_chart
from data import fetcher


def render():
    uid = st.session_state["user"]["user_id"]
    today = today_str()
    colors = get_theme_color(THEME_LIGHT)

    st.title("📝 每日复盘")
    review_date = st.date_input("复盘日期", value=date.today(), key="review_date_picker")
    date_str = review_date.isoformat()

    # 加载已有复盘
    existing = db.get_review_journal(uid, date_str)

    tab1, tab2, tab3 = st.tabs(["📊 大盘诊断", "📋 自选股表现", "✍️ 复盘笔记"])

    with tab1:
        st.subheader("指数走势")
        index_data = fetcher.get_index_data_for_review()
        if index_data and index_data.get("sh"):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("上证", f"{index_data['sh']['close']:.2f}",
                          f"{index_data['sh']['change_pct']:+.2f}%")
            with c2:
                st.metric("深证", f"{index_data['sz']['close']:.2f}" if index_data.get('sz') else "--",
                          f"{index_data['sz']['change_pct']:+.2f}%" if index_data.get('sz') else "")
            with c3:
                st.metric("创业板", f"{index_data['cy']['close']:.2f}" if index_data.get('cy') else "--",
                          f"{index_data['cy']['change_pct']:+.2f}%" if index_data.get('cy') else "")
        else:
            st.info("暂无大盘数据，请先同步行情")

        snapshot = db.get_today_market_snapshot(today)
        if snapshot:
            st.caption(f"市场情绪: {make_sentience_label(snapshot['sentiment'])}")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("涨停家数", snapshot.get("limit_up_count", 0))
            with c2:
                st.metric("跌停家数", snapshot.get("limit_down_count", 0))

    with tab2:
        st.subheader("自选股今日表现")
        daily_data = db.get_watchlist_daily(uid, date_str)
        if daily_data:
            rows = []
            for row in daily_data:
                rows.append({
                    "代码": row["stock_code"],
                    "名称": row["stock_name"],
                    "收盘价": row["close_price"],
                    "涨跌幅": f"{row['change_pct']:+.2f}%" if row["change_pct"] else "--",
                    "量比": f"{row['volume_ratio']:.2f}" if row["volume_ratio"] else "--",
                    "状态": row["status"] or "正常",
                })
            import pandas as pd
            df = pd.DataFrame(rows)
            st.dataframe(df, hide_index=True, use_container_width=True)

            # 个股K线
            st.subheader("个股K线图")
            stock_codes = db.get_watchlist(uid)
            code_options = {f"{s['code']} {s['name'] or ''}": s['code'] for s in stock_codes}
            if code_options:
                selected = st.selectbox("选择个股查看K线", list(code_options.keys()))
                if selected:
                    code = code_options[selected]
                    kdf = fetcher.fetch_kline_data(code, (date.today() - __import__('datetime').timedelta(days=180)).isoformat())
                    if kdf is not None and not kdf.empty:
                        fig = kline_chart(kdf)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("K线数据暂不可用（交易时段外或接口限制）")
        else:
            st.info("暂无今日自选股数据，请先同步行情或添加自选股")

    with tab3:
        st.subheader("复盘笔记")

        market_diag = st.text_area("大盘诊断", value=existing["market_diagnosis"] if existing else "",
                                   height=100, key="diag")
        sector_rot = st.text_area("板块轮动分析", value=existing["sector_rotation"] if existing else "",
                                  height=80, key="sector")
        limit_up_ana = st.text_area("涨停分析", value=existing["limit_up_analysis"] if existing else "",
                                    height=80, key="limitup")
        personal = st.text_area("操作回顾与反思", value=existing["personal_review"] if existing else "",
                                height=120, key="personal")

        c1, c2 = st.columns(2)
        with c1:
            emotion = st.slider("情绪评分", 1, 10,
                                value=existing["emotion_score"] if existing else 5, key="emotion")
        with c2:
            discipline = st.slider("纪律评分", 1, 10,
                                   value=existing["discipline_score"] if existing else 5, key="discipline")

        plan = st.text_area("次日计划", value=existing["plan_for_tomorrow"] if existing else "",
                            height=80, key="plan")

        if st.button("💾 保存复盘", type="primary"):
            db.upsert_review_journal(
                uid, date_str, market_diag, sector_rot, limit_up_ana,
                personal, emotion, discipline, plan,
            )
            st.success("复盘已保存")

        if st.button("📄 导出报告"):
            st.info("报告导出功能开发中")

