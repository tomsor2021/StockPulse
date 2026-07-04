# -*- coding: utf-8 -*-
"""StockPulse 主入口"""
import streamlit as st
import os
import sys

# 确保项目根目录在 path 中
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 开发模式：强制重载 views 模块以获取最新代码
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith("views.") or mod_name == "views":
        del sys.modules[mod_name]

from config.settings import CSS_PATH
from database.db import init_database
from database.migrations import run_migrations
from utils.logger import setup_logging

# ── 初始化 ──
logger = setup_logging()
init_database()
run_migrations()

# ── 页面配置 ──
st.set_page_config(
    page_title="StockPulse",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义 CSS
if CSS_PATH.exists():
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── 会话管理 ──
if "user" not in st.session_state:
    st.session_state["user"] = None

user = st.session_state.get("user")

# ── 自动登录（开发测试用）──
if user is None:
    query_params = st.query_params
    auto_user = query_params.get("auto_user")
    auto_pw = query_params.get("auto_pw")
    if auto_user and auto_pw:
        from auth.auth import authenticate_user
        auto_result = authenticate_user(auto_user, auto_pw)
        if auto_result:
            st.session_state["user"] = auto_result
            user = auto_result

# ── 未登录：仅显示登录页 ──
if user is None or not isinstance(user, dict) or not user.get("user_id"):
    from auth.forms import show_login_page
    show_login_page()
    st.stop()

# ── 已登录：侧边栏 + 页面渲染 ──
display_name = user.get("nickname") or user.get("username") or "用户"

with st.sidebar:
    st.markdown("### 📊 StockPulse")
    st.markdown(f"👤 **{display_name}**")
    st.divider()

    from views import dashboard, daily_review, watchlist, trades, journal, settings
    from auth.forms import logout

    page = st.navigation([
        st.Page(dashboard.render, title="首页看板", icon="📊", default=True, url_path="dashboard"),
        st.Page(daily_review.render, title="每日复盘", icon="📝", url_path="daily_review"),
        st.Page(watchlist.render, title="自选股池", icon="⭐", url_path="watchlist"),
        st.Page(trades.render, title="交易记录", icon="💰", url_path="trades"),
        st.Page(journal.render, title="复盘日志", icon="📖", url_path="journal"),
        st.Page(settings.render, title="系统设置", icon="⚙️", url_path="settings"),
    ])

    st.divider()
    if st.button("🚪 退出登录", width="stretch"):
        logout()

page.run()
