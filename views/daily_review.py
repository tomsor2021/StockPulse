"""每日复盘页面"""
import streamlit as st
from datetime import date, datetime, timedelta
from database import models as db
from config.theme import get_theme_color
from config.settings import THEME_LIGHT
from utils.helpers import today_str, make_sentience_label
from components.kline import kline_chart
from components.cards import market_metric
from data import fetcher, sync, cache


def render():
    uid = st.session_state["user"]["user_id"]
    today = today_str()
    colors = get_theme_color(THEME_LIGHT)

    st.title("📝 每日复盘")
    review_date = st.date_input("复盘日期", value=date.today(), key="review_date_picker")
    date_str = review_date.isoformat()

    snapshot = db.get_today_market_snapshot(today)
    snapshot = dict(snapshot) if snapshot else {}

    col_refresh, col_status = st.columns([1, 3])
    with col_refresh:
        if st.button("🔄 刷新数据"):
            progress_bar = st.progress(0, text="正在同步...")
            def progress_cb(pct, msg):
                progress_bar.progress(pct, text=msg)
            sync.sync_all(uid, progress_callback=progress_cb)
            st.cache_data.clear()
            st.success("数据已更新")
            st.rerun()

    with col_status:
        cache_info = cache.get_cache_info()
        last_fetch = cache.get_last_fetch_time()

        if snapshot and snapshot.get("created_at"):
            db_time_str = snapshot["created_at"][:19]

            if cache_info:
                st.info(f"🗄️ 缓存数据 | 数据更新时间: {db_time_str} | 缓存时间: {last_fetch.strftime('%H:%M:%S') if last_fetch else '--'}")
            else:
                st.info(f"⬇️ 实时数据 | 数据更新时间: {db_time_str}")
        else:
            if cache_info:
                st.info(f"🗄️ 缓存数据 | 缓存时间: {last_fetch.strftime('%Y-%m-%d %H:%M:%S') if last_fetch else '--'}")
            else:
                st.warning("⚠️ 暂无数据")

    # 加载已有复盘
    existing = db.get_review_journal(uid, date_str)
    existing = dict(existing) if existing else None

    tab1, tab2, tab3 = st.tabs(["📊 大盘诊断", "📋 自选股表现", "✍️ 复盘笔记"])

    with tab1:
        st.subheader("指数走势")
        index_data = fetcher.get_index_data_for_review()
        if index_data and index_data.get("sh"):
            c1, c2, c3 = st.columns(3)
            with c1:
                market_metric("上证", index_data['sh']['close'], index_data['sh']['change_pct'])
            with c2:
                market_metric("深证", index_data['sz']['close'] if index_data.get('sz') else None,
                              index_data['sz']['change_pct'] if index_data.get('sz') else None)
            with c3:
                market_metric("创业板", index_data['cy']['close'] if index_data.get('cy') else None,
                              index_data['cy']['change_pct'] if index_data.get('cy') else None)
        else:
            st.info("暂无大盘数据，请先同步行情")

        snapshot = db.get_today_market_snapshot(today)
        snapshot = dict(snapshot) if snapshot else None
        if snapshot:
            st.caption(f"市场情绪: {make_sentience_label(snapshot['sentiment'])}")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("涨停家数", snapshot.get("limit_up_count", 0))
            with c2:
                st.metric("跌停家数", snapshot.get("limit_down_count", 0))

    with tab2:
        daily_data = db.get_watchlist_daily(uid, date_str)
        st.subheader(f"自选股今日表现（{len(daily_data)}只）")
        if daily_data:
            rows = []
            for row in daily_data:
                change_val = row["change_pct"]
                rows.append({
                    "代码": row["stock_code"],
                    "名称": row["stock_name"],
                    "收盘价": row["close_price"],
                    "涨跌幅": change_val,
                    "量比": f"{row['volume_ratio']:.2f}" if row["volume_ratio"] else "--",
                    "状态": row["status"] or "正常",
                })
            import pandas as pd
            df = pd.DataFrame(rows)

            # 涨跌幅颜色
            def _color_change(val):
                if val is None:
                    return ""
                if val > 0:
                    return "color: #D32F2F; font-weight: 500;"
                elif val < 0:
                    return "color: #2E7D32; font-weight: 500;"
                return ""

            df_styled = df.style.map(_color_change, subset=["涨跌幅"])
            st.dataframe(
                df_styled,
                column_config={
                    "涨跌幅": st.column_config.NumberColumn(format="%.2f%%"),
                },
                hide_index=True,
                width="stretch",
            )

            # 个股K线
            st.subheader("个股K线图")
            stock_codes = db.get_watchlist(uid)
            code_options = {f"{s['code']} {s['name'] or ''}": s['code'] for s in stock_codes}
            if code_options:
                selected = st.selectbox("选择个股查看K线", list(code_options.keys()))
                if selected:
                    code = code_options[selected]
                    kdf = fetcher.fetch_kline_data(code, (date.today() - timedelta(days=180)).isoformat())
                    if kdf is not None and not kdf.empty:
                        fig = kline_chart(kdf)
                        if fig:
                            st.plotly_chart(fig, width="stretch")
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