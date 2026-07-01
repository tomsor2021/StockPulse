"""StockPulse 主入口"""
import streamlit as st
import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 强制清除 pages 模块缓存
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith('pages'):
        del sys.modules[mod_name]

from config.settings import CSS_PATH
from config.theme import get_theme_color
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

# ── 登录/注册 ──
if not st.session_state["user"]:
    from auth.forms import show_login_page
    show_login_page()
    st.stop()

# ── 已登录：侧边栏导航 ──
user = st.session_state.get("user")

# 安全检查：user 可能为 None
if not user:
    from auth.forms import show_login_page
    show_login_page()
    st.stop()

with st.sidebar:
    st.markdown(f"### 📊 StockPulse")
    display_name = user.get('nickname') if user.get('nickname') else user.get('username', '用户')
    st.markdown(f"👤 **{display_name}**")
    st.divider()

    # 页面导航
    from pages import dashboard, daily_review, watchlist, trades, journal, settings
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
    if st.button("🚪 退出登录", use_container_width=True):
        logout()

# ── 渲染选中页面 ──
page.run()
