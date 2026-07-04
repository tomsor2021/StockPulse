"""首页看板"""
import streamlit as st
import pandas as pd
import requests
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict
from database import models as db
from data import sync, cache, fetcher
from config.theme import get_theme_color, color_change, arrow_change
from config.settings import THEME_LIGHT
from utils.helpers import format_pct, format_money, today_str
from components.cards import market_index_card, stat_card, alert_item, market_metric


@st.cache_data(ttl=60, show_spinner="加载全球指数...")
def _get_cached_global_data():
    return fetcher.get_global_index_data()

@st.cache_data(ttl=60, show_spinner="加载指数行情...")
def _get_cached_index_data():
    return fetcher.get_index_data_for_review()

@st.cache_data(ttl=300, show_spinner=False)
def _get_cached_articles() -> List[Dict]:
    """从新浪财经 API 获取最新财经文章"""
    logger = logging.getLogger("stockpulse.dashboard")
    _SINA_API = "https://feed.mix.sina.com.cn/api/roll/get"
    _HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(
            _SINA_API,
            params={"pageid": 153, "lid": 2509, "k": "", "num": 10},
            headers=_HEADERS,
            timeout=8,
        )
        r.raise_for_status()
        data = r.json()
        items = []
        for item in data.get("result", {}).get("data", [])[:8]:
            title = item.get("title", "").strip()
            url = item.get("url", "").strip()
            source = item.get("media_name", "").strip()
            ctime = item.get("ctime", "")
            if title and url:
                if ctime:
                    try:
                        ctime = datetime.fromtimestamp(int(ctime)).strftime("%m-%d %H:%M")
                    except:  # noqa: E722
                        pass
                items.append({"title": title, "url": url, "source": source, "ctime": ctime})
        return items
    except Exception as e:
        logger.warning(f"新浪财经文章获取失败: {e}")
        return []

def render():
    colors = get_theme_color(THEME_LIGHT)
    uid = st.session_state["user"]["user_id"]
    today = today_str()
    user_data = st.session_state["user"]
    display_name = user_data.get('nickname') or user_data.get('username', '用户')

    st.title("首页看板")
    st.caption(f"欢迎回来，{display_name}")

    # 大盘状态 + 统计
    snapshot = db.get_today_market_snapshot(today)
    if not snapshot:
        snapshot = db.get_latest_market_snapshot()
    snapshot = dict(snapshot) if snapshot else {}

    # 数据刷新
    col_refresh, col_status = st.columns([1, 3])
    with col_refresh:
        if st.button("🔄 刷新数据"):
            progress_bar = st.progress(0, text="正在同步...")
            status_text = st.empty()
            def progress_cb(pct, msg):
                progress_bar.progress(pct, text=msg)
            sync.sync_all(uid, progress_callback=progress_cb)
            st.cache_data.clear()
            status_text.success("数据已更新")
            st.rerun()
    
    with col_status:
        cache_info = cache.get_cache_info()
        last_fetch = cache.get_last_fetch_time()
        
        if snapshot and snapshot.get("created_at"):
            db_time_str = snapshot["created_at"][:19]
            db_time = datetime.strptime(db_time_str, "%Y-%m-%d %H:%M:%S")
            
            if cache_info:
                st.info(f"🗄️ 缓存数据 | 数据更新时间: {db_time_str} | 缓存时间: {last_fetch.strftime('%H:%M:%S') if last_fetch else '--'}")
            else:
                st.info(f"⬇️ 实时数据 | 数据更新时间: {db_time_str}")
        else:
            if cache_info:
                st.info(f"🗄️ 缓存数据 | 缓存时间: {last_fetch.strftime('%Y-%m-%d %H:%M:%S') if last_fetch else '--'}")
            else:
                st.warning("⚠️ 暂无数据")

    index_data = _get_cached_index_data()
    global_data = _get_cached_global_data()
    articles = _get_cached_articles()

    # 第一行：A股四大指数
    st.subheader("📊 A股指数")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sh = (index_data.get("sh") or {}) if index_data else {}
        sh_close = sh.get("close") or snapshot.get("sh_close")
        sh_chg = sh.get("change_pct") or snapshot.get("sh_change_pct")
        sh_vol = sh.get("volume") or snapshot.get("sh_volume")
        market_metric("上证指数", sh_close, sh_chg)
    with c2:
        sz = (index_data.get("sz") or {}) if index_data else {}
        sz_close = sz.get("close") or snapshot.get("sz_close")
        sz_chg = sz.get("change_pct") or snapshot.get("sz_change_pct")
        sz_vol = sz.get("volume") or snapshot.get("sz_volume")
        market_metric("深证成指", sz_close, sz_chg)
    with c3:
        cy = (index_data.get("cy") or {}) if index_data else {}
        cy_close = cy.get("close") or snapshot.get("cy_close")
        cy_chg = cy.get("change_pct") or snapshot.get("cy_change_pct")
        cy_vol = cy.get("volume") or snapshot.get("cy_volume")
        market_metric("创业板指", cy_close, cy_chg)
    with c4:
        kc = (index_data.get("kc") or {}) if index_data else {}
        market_metric("科创板指", kc.get("close"), kc.get("change_pct"))

    # ── 当日大盘走势分析 ──
    snap = dict(snapshot) if snapshot else {}
    sh_chg_str = f"{sh_chg:+.2f}%" if sh_chg is not None else "--"
    sz_chg_str = f"{sz_chg:+.2f}%" if sz_chg is not None else "--"
    cy_chg_str = f"{cy_chg:+.2f}%" if cy_chg is not None else "--"
    limit_up = snap.get("limit_up_count", 0)
    limit_down = snap.get("limit_down_count", 0)
    
    # 涨跌方向描述
    changes = [x for x in [sh_chg, sz_chg, cy_chg] if x is not None]
    if changes:
        up_cnt = sum(1 for x in changes if x > 0)
        if up_cnt == len(changes):
            trend = "📈 三大指数集体上涨"
        elif up_cnt == 0:
            trend = "📉 三大指数集体下跌"
        else:
            trend = "📊 三大指数涨跌互现"
    else:
        trend = "暂无当日数据"
    
    # 市场情绪
    if limit_up or limit_down:
        ratio = limit_up / max(limit_down, 1)
        if ratio >= 4:
            mood = "市场情绪偏热，做多意愿较强"
        elif ratio <= 0.25:
            mood = "市场情绪偏冷，做多意愿不足"
        else:
            mood = "市场情绪中性，多空相对均衡"
    else:
        mood = ""
    
    st.markdown(f"""
    <div style="background:#F5F7FA;padding:12px 16px;border-radius:8px;margin:8px 0 12px 0;font-size:14px;line-height:1.7">
        <div style="font-weight:600;margin-bottom:4px">{trend}</div>
        <div style="display:flex;gap:20px;color:#555">
            <span>上证 {sh_chg_str}</span>
            <span>深证 {sz_chg_str}</span>
            <span>创业板 {cy_chg_str}</span>
        </div>
        <div style="color:#777;margin-top:4px">
            涨停 {limit_up} 家 · 跌停 {limit_down} 家{' · ' + mood if mood else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # —— 机构观点 ——
    with st.expander("📰 机构观点", expanded=False):
        if not articles:
            st.markdown("<span style='color:#999;font-size:13px'>暂无最新文章</span>", unsafe_allow_html=True)
        else:
            lines = []
            for a in articles:
                tag = f"[{a['source']}]" if a["source"] else ""
                time = a.get("ctime", "")
                time_tag = f"<span style='color:#aaa;font-size:12px'>{time}</span>" if time else ""
                lines.append(
                    f"- [{a['title']}]({a['url']}) {tag} {time_tag}"
                )
            st.markdown("\n".join(lines), unsafe_allow_html=True)
    # 第二行：全球指数
    st.subheader("🌍 全球指数")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        hsi = (global_data.get("hsi") or {}) if global_data else {}
        hsi_close = hsi.get("close")
        hsi_chg = hsi.get("change_pct")
        market_metric("恒生指数", hsi_close, hsi_chg)
    with c2:
        nikkei = (global_data.get("nikkei") or {}) if global_data else {}
        nk_close = nikkei.get("close")
        nk_chg = nikkei.get("change_pct")
        market_metric("日经225", nk_close, nk_chg)
    with c3:
        sp500 = (global_data.get("sp500") or {}) if global_data else {}
        sp_close = sp500.get("close")
        sp_chg = sp500.get("change_pct")
        market_metric("标普500", sp_close, sp_chg)
    with c4:
        nasdaq = (global_data.get("nasdaq") or {}) if global_data else {}
        nd_close = nasdaq.get("close")
        nd_chg = nasdaq.get("change_pct")
        market_metric("纳斯达克", nd_close, nd_chg)

    # ── 全球指数走势分析 ──
    hsi_chg_str = f"{hsi_chg:+.2f}%" if hsi_chg is not None else "--"
    nk_chg_str = f"{nk_chg:+.2f}%" if nk_chg is not None else "--"
    sp_chg_str = f"{sp_chg:+.2f}%" if sp_chg is not None else "--"
    nd_chg_str = f"{nd_chg:+.2f}%" if nd_chg is not None else "--"
    
    g_changes = [x for x in [hsi_chg, nk_chg, sp_chg, nd_chg] if x is not None]
    if g_changes:
        g_up_cnt = sum(1 for x in g_changes if x > 0)
        if g_up_cnt == len(g_changes):
            g_trend = "🌍 全球主要指数集体上涨"
        elif g_up_cnt == 0:
            g_trend = "🌍 全球主要指数集体下跌"
        else:
            g_trend = "🌍 全球主要指数涨跌互现"
    else:
        g_trend = "暂无当日数据"
    
    st.markdown(f"""
    <div style="background:#F5F7FA;padding:12px 16px;border-radius:8px;margin:8px 0 12px 0;font-size:14px;line-height:1.7">
        <div style="font-weight:600;margin-bottom:4px">{g_trend}</div>
        <div style="display:flex;gap:20px;color:#555">
            <span>恒生 {hsi_chg_str}</span>
            <span>日经 {nk_chg_str}</span>
            <span>标普 {sp_chg_str}</span>
            <span>纳斯达克 {nd_chg_str}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 第三行：市场统计
    st.subheader("📈 市场统计")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("涨停", snapshot["limit_up_count"] if snapshot else 0, "家")
    with c2:
        stat_card("跌停", snapshot["limit_down_count"] if snapshot else 0, "家")
    with c3:
        positions = db.get_current_positions(uid)
        stat_card("持仓", len(positions), "只")
    with c4:
        from database.models import calculate_win_rate_detail
        wr = calculate_win_rate_detail(uid, 20)
        stat_card("胜率", f"{wr['rate']}%", f"{wr['wins']}/{wr['total']}")

    # 今日盈亏 + 持仓占比 + 待办
    c_left, c_right = st.columns([3, 2])

    with c_left:
        st.subheader("📊 当前持仓")
        if positions:
            pos_df = pd.DataFrame(positions)
            st.dataframe(pos_df[["code", "name", "hold_qty", "cost", "total_cost"]],
                         column_config={"code": "代码", "name": "名称", "hold_qty": "持股数",
                                        "cost": "成本价", "total_cost": st.column_config.NumberColumn("总成本", format="%.2f")},
                         hide_index=True, width="stretch")
        else:
            st.info("暂无持仓数据")

        # 持仓占比饼图
        if positions:
            st.subheader("📈 持仓占比")
            import plotly.graph_objects as go
            labels = [p["name"] or p["code"] for p in positions[:8]]
            values = [p["total_cost"] for p in positions[:8]]
            if len(positions) > 8:
                labels.append("其他")
                values.append(sum(p["total_cost"] for p in positions[8:]))
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
            fig.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, width="stretch")

    with c_right:
        st.subheader("📝 待办事项")
        todos = db.get_todos(uid)
        for idx, todo in enumerate(todos):
            todo_dict = dict(todo)
            c = st.columns([4, 1])
            with c[0]:
                is_done = st.checkbox(todo_dict["content"], value=todo_dict.get("is_done", False),
                                      key=f"todo_chk_{todo_dict['id']}",
                                      on_change=lambda tid=todo_dict['id']: db.toggle_todo(tid, uid))
            with c[1]:
                if st.button("删除", key=f"del_todo_{todo_dict['id']}_{idx}"):
                    db.delete_todo(todo_dict["id"], uid)
                    st.rerun()
        new_todo = st.text_input("添加待办", placeholder="输入待办事项...", key="new_todo_input")
        if st.button("添加", key="add_todo_btn"):
            if new_todo.strip():
                db.add_todo(uid, new_todo.strip())
                st.rerun()

        # 今日提醒
        st.subheader("🔔 今日提醒")
        alerts = db.get_today_alerts(uid)
        if alerts:
            for alert in alerts:
                alert_item(alert["stock_name"] or alert["stock_code"], alert["alert_type"],
                           alert["message"], alert["id"], uid, lambda aid, uid: db.mark_alert_read(aid, uid))
        else:
            st.info("暂无今日提醒")
