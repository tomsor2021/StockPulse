"""系统设置页面"""
import streamlit as st
from database import models as db
from config.settings import THEME_LIGHT, THEME_DARK, THEME_SYSTEM
from config.theme import get_theme_color
from auth.forms import show_account_settings
from data import sync
from utils.logger import get_recent_log_lines


def render():
    uid = st.session_state["user"]["user_id"]
    colors = get_theme_color(THEME_LIGHT)
    st.title("⚙️ 系统设置")

    tabs = st.tabs(["🔔 提醒设置", "📡 数据源", "🎨 主题", "👤 账户", "📂 数据管理", "📋 系统日志"])

    with tabs[0]:
        st.subheader("提醒设置")
        alert_enabled = st.toggle("全局提醒开关",
                                   value=db.get_setting(uid, "alert_enabled", "true") == "true",
                                   key="alert_enabled")
        db.set_setting(uid, "alert_enabled", str(alert_enabled).lower())

        c1, c2 = st.columns(2)
        with c1:
            up_threshold = st.number_input("涨停提醒阈值 (%)", value=9.8, step=0.5, key="up_thr")
            down_threshold = st.number_input("跌停提醒阈值 (%)", value=-9.8, step=0.5, key="down_thr")
        with c2:
            vol_threshold = st.number_input("放量倍数阈值", value=3.0, step=0.5, key="vol_thr")
            dingtalk_webhook = st.text_input("钉钉 Webhook URL", type="password",
                                              value=db.get_setting(uid, "dingtalk_webhook", ""),
                                              key="dingtalk_url", help="留空则不启用钉钉推送")

        if st.button("保存提醒设置", key="save_alert_settings"):
            db.set_setting(uid, "alert_up_pct", str(up_threshold))
            db.set_setting(uid, "alert_down_pct", str(down_threshold))
            db.set_setting(uid, "alert_volume_ratio", str(vol_threshold))
            if dingtalk_webhook:
                db.set_setting(uid, "dingtalk_webhook", dingtalk_webhook)
            st.success("提醒设置已保存")

    with tabs[1]:
        st.subheader("数据源设置")
        current_source = db.get_system_config("data_source", "AKShare")
        source = st.radio("默认行情源", ["AKShare", "Baostock"],
                          index=0 if current_source == "AKShare" else 1, key="data_source")
        retries = st.number_input("重试次数", value=3, min_value=1, max_value=10, key="retries")
        timeout = st.number_input("请求超时（秒）", value=10, min_value=5, max_value=60, key="timeout")

        if st.button("保存数据源设置"):
            db.set_system_config("data_source", source)
            st.success("数据源设置已保存")

        st.divider()
        if st.button("🔄 立即同步数据", type="primary"):
            progress_bar = st.progress(0, text="正在同步...")
            def progress_cb(pct, msg):
                progress_bar.progress(pct, text=msg)
            sync.sync_all(uid, progress_cb)
            st.success("数据同步完成")

    with tabs[2]:
        st.subheader("主题设置")
        current_theme = db.get_system_config("theme", THEME_LIGHT)
        theme = st.radio("主题切换", [THEME_LIGHT, THEME_DARK, THEME_SYSTEM],
                         index=[THEME_LIGHT, THEME_DARK, THEME_SYSTEM].index(current_theme)
                         if current_theme in [THEME_LIGHT, THEME_DARK, THEME_SYSTEM] else 0,
                         key="theme_select")
        if st.button("应用主题"):
            db.set_system_config("theme", theme)
            st.success(f"主题已切换为 {theme}，刷新页面后生效")

    with tabs[3]:
        show_account_settings()

    with tabs[4]:
        st.subheader("数据管理")

        if st.button("📤 导出我的数据"):
            st.info("导出功能开发中")

        if st.button("📥 导入数据"):
            st.info("导入功能开发中")

        st.divider()
        st.warning("⚠️ 重置将清空该用户的所有交易记录、自选股、复盘日志等数据，此操作不可恢复！")
        confirm = st.text_input("输入「确认重置」以继续", key="reset_confirm")
        if st.button("🗑 重置所有数据", type="primary"):
            if confirm == "确认重置":
                from database.models import delete_user
                db.delete_user(uid)
                st.session_state.clear()
                st.success("数据已重置")
                st.rerun()
            else:
                st.error("请输入「确认重置」")

    with tabs[5]:
        st.subheader("系统日志")
        log_lines = get_recent_log_lines(100)
        st.text_area("最近 100 行日志", value=log_lines, height=400, disabled=True)

