"""复盘日志页面"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database import models as db
from utils.helpers import truncate_text


def render():
    uid = st.session_state["user"]["user_id"]
    st.title("📖 复盘日志")

    # 日历概览
    dates_with_journals = db.get_all_review_dates(uid)
    if dates_with_journals:
        st.caption(f"📅 共有 {len(dates_with_journals)} 天有复盘记录")

    # 选择日期
    view_date = st.date_input("查看日期", value=date.today(), key="journal_date")
    date_str = view_date.isoformat()

    journal = db.get_review_journal(uid, date_str)

    col1, col2 = st.columns([3, 1])
    with col1:
        if journal:
            st.subheader(f"📝 {date_str} 复盘")
            with st.expander("大盘诊断", expanded=True):
                st.write(journal.get("market_diagnosis") or "无记录")
            with st.expander("板块轮动分析"):
                st.write(journal.get("sector_rotation") or "无记录")
            with st.expander("涨停分析"):
                st.write(journal.get("limit_up_analysis") or "无记录")
            with st.expander("操作回顾"):
                st.write(journal.get("personal_review") or "无记录")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("情绪评分", f"{journal['emotion_score']}/10" if journal.get("emotion_score") else "未评分")
            with c2:
                st.metric("纪律评分", f"{journal['discipline_score']}/10" if journal.get("discipline_score") else "未评分")
            with st.expander("次日计划"):
                st.write(journal.get("plan_for_tomorrow") or "无记录")

            if st.button("🗑 删除此日志", type="secondary"):
                db.delete_review_journal(journal["id"], uid)
                st.success("已删除")
                st.rerun()
        else:
            st.info(f"{date_str} 暂无复盘记录，请前往「每日复盘」页面创建")

    with col2:
        st.subheader("近期日志")
        journals = db.get_review_journals(uid, 30)
        for j in journals[:10]:
            if st.button(f"{j['review_date']} ⭐{j['emotion_score'] or '?'}/10",
                         key=f"j_{j['id']}", use_container_width=True):
                # 这里简化处理，直接跳转日期选择
                st.session_state["journal_date"] = date.fromisoformat(j["review_date"])
                st.rerun()

