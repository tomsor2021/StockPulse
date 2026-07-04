"""自选股池页面"""
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from database import models as db
from data import sync, cache
from config.settings import WATCHLIST_GROUPS
from utils.helpers import parse_stock_code, today_str
from components.kline import kline_chart
from data import fetcher


def render():
    uid = st.session_state["user"]["user_id"]
    today = today_str()
    st.title("⭐ 自选股池")

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

    tabs = st.tabs(WATCHLIST_GROUPS)
    for idx, group in enumerate(WATCHLIST_GROUPS):
        with tabs[idx]:
            _render_group(uid, group)


def _render_group(uid, group_name):
    # 添加自选股
    with st.expander("➕ 添加自选股", expanded=False):
        c1, c2 = st.columns([2, 1])
        with c1:
            code_input = st.text_input("股票/基金代码", placeholder="例如 A股 000001 / 港股 06869 / 基金 510300", 
                                       key=f"add_code_{group_name}")
        
        with c2:
            note_input = st.text_input("备注（选填）", key=f"add_note_{group_name}")
        
        # 实时查询股票/基金名称（支持A股6位、港股5位、基金6位）
        stock_name = None
        code = ""
        if code_input.strip():
            code = parse_stock_code(code_input.strip())
            if len(code) in (5, 6):
                stock_name = fetcher.fetch_stock_name(code)
        
        # 显示股票/基金名称
        if stock_name:
            st.markdown(f"<span style='color:#4CAF50; font-weight:500'>📌 {stock_name}</span>", unsafe_allow_html=True)
        elif code and len(code) in (5, 6):
            st.markdown("<span style='color:#9E9E9E'>❓ 未查询到名称</span>", unsafe_allow_html=True)
        
        if st.button("添加", key=f"add_btn_{group_name}"):
            if not code_input.strip():
                st.warning("请输入股票代码")
                return
            code = parse_stock_code(code_input.strip())
            if len(code) not in (5, 6):
                st.warning("股票代码必须是5位（港股）或6位（A股）数字")
                return
            
            existing = db.get_watchlist_stock(uid, code, group_name)
            if existing:
                st.warning(f"该股票已在{group_name}中")
                return
            
            name = stock_name or code
            if not stock_name:
                st.info(f"未查询到股票名称，使用代码 {code} 作为名称")
            
            db.add_watchlist_stock(uid, code, name, group_name, note_input)
            st.success(f"已添加 {name}")
            st.rerun()

    # 股票列表
    stocks = db.get_watchlist(uid, group_name)
    if not stocks:
        st.info("该分组暂无自选股")
        return

    today = date.today().isoformat()
    
    daily_data = db.get_watchlist_daily(uid, today)
    daily_dict = {d["stock_code"]: dict(d) for d in daily_data}

    col_refresh, _ = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 刷新行情", key=f"refresh_{group_name}"):
            try:
                sync._sync_watchlist_daily(uid, today)
                daily_data = db.get_watchlist_daily(uid, today)
                daily_dict = {d["stock_code"]: dict(d) for d in daily_data}
                st.success("行情已更新")
            except Exception as e:
                st.error(f"刷新失败: {e}")

    # 初始化选中状态字典
    if f"selected_map_{group_name}" not in st.session_state:
        st.session_state[f"selected_map_{group_name}"] = {}

    # 全选复选框
    col_select_all, _ = st.columns([1, 9])
    with col_select_all:
        select_all = st.checkbox("全选", key=f"select_all_{group_name}",
                                  value=all(st.session_state[f"selected_map_{group_name}"].get(f"chk_{s['code']}_{group_name}", False) for s in stocks) if stocks else False)
    
    if select_all:
        for s in stocks:
            st.session_state[f"selected_map_{group_name}"][f"chk_{s['code']}_{group_name}"] = True
    else:
        for s in stocks:
            st.session_state[f"selected_map_{group_name}"][f"chk_{s['code']}_{group_name}"] = False

    # 渲染带复选框的股票列表
    for s in stocks:
        d = daily_dict.get(s["code"], {})
        change = d.get("change_pct")
        change_str = f"{'📈' if change and change > 0 else '📉' if change and change < 0 else ''}{change:+.2f}%" if change else "-"
        close_price = d.get("close_price") or 0
        
        chk_key = f"chk_{s['code']}_{group_name}"
        is_selected = st.session_state[f"selected_map_{group_name}"].get(chk_key, False)
        
        col_check, col_code, col_name, col_price, col_change, col_note = st.columns([1, 2, 3, 2, 2, 4])
        with col_check:
            checked = st.checkbox("", value=is_selected, key=chk_key)
            st.session_state[f"selected_map_{group_name}"][chk_key] = checked
        
        with col_code:
            st.write(f"**{s['code']}**")
        
        with col_name:
            st.write(s["name"] or "-")
        
        with col_price:
            st.write(f"{close_price:.2f}")
        
        with col_change:
            st.markdown(f"<span style='{'color:red' if change and change > 0 else 'color:green' if change and change < 0 else 'color:gray'}'>{change_str}</span>", unsafe_allow_html=True)
        
        with col_note:
            st.write(s["note"] or "-")

    # 从选中映射中获取选中的股票代码列表
    selected_stocks = [s["code"] for s in stocks if st.session_state[f"selected_map_{group_name}"].get(f"chk_{s['code']}_{group_name}", False)]
    
    # 操作区
    st.divider()
    
    if len(selected_stocks) > 0:
        st.info(f"已选择 {len(selected_stocks)} 只股票")
        
        action = st.radio("操作类型", ["编辑备注", "提醒设置", "查看K线图", "移动到", "复制到", "删除"], key=f"action_{group_name}")
        
        if action == "编辑备注":
            if len(selected_stocks) == 1:
                code = selected_stocks[0]
                stock = db.get_watchlist_stock(uid, code, group_name)
                current_note = stock["note"] if stock else ""
                new_note = st.text_area("备注内容", value=current_note, key=f"note_edit_{group_name}", height=100)
                if st.button("保存备注", key=f"save_note_{group_name}"):
                    db.update_watchlist_stock(uid, code, group_name=group_name, note=new_note)
                    st.success("备注已保存")
                    st.rerun()
            else:
                st.warning("编辑备注只能针对单只股票，请选择一只股票")
        
        elif action == "提醒设置":
            if len(selected_stocks) == 1:
                code = selected_stocks[0]
                stock = db.get_watchlist_stock(uid, code, group_name)
                col1, col2 = st.columns(2)
                with col1:
                    up = st.number_input("涨幅提醒(%)", value=stock["alert_up_pct"] or 9.8, step=0.1, key=f"up_{group_name}")
                    down = st.number_input("跌幅提醒(%)", value=stock["alert_down_pct"] or -9.8, step=0.1, key=f"down_{group_name}")
                with col2:
                    vol = st.number_input("放量倍数", value=stock["alert_volume_ratio"] or 3.0, step=0.1, key=f"vol_{group_name}")
                    bp = st.number_input("破位价格", value=stock["alert_break_price"] or 0.0, step=0.01, key=f"bp_{group_name}")
                if st.button("保存提醒设置", key=f"save_alert_{group_name}"):
                    db.update_watchlist_stock(uid, code, group_name=group_name,
                                              alert_up_pct=up, alert_down_pct=down,
                                              alert_volume_ratio=vol, alert_break_price=bp)
                    st.success("提醒设置已保存")
                    st.rerun()
            else:
                st.warning("提醒设置只能针对单只股票，请选择一只股票")
        
        elif action == "查看K线图":
            if len(selected_stocks) == 1:
                code = selected_stocks[0]
                stock = db.get_watchlist_stock(uid, code, group_name)
                st.subheader(f"📈 {stock['name'] or code} K线图")
                start = (date.today() - timedelta(days=180)).isoformat()
                kdf = fetcher.fetch_kline_data(code, start)
                if kdf is not None and not kdf.empty:
                    fig = kline_chart(kdf)
                    if fig:
                        st.plotly_chart(fig, width="stretch", key=f"kline_{group_name}")
                else:
                    st.info("K线数据暂不可用")
            else:
                st.warning("查看K线图只能针对单只股票，请选择一只股票")
        
        elif action == "移动到":
            target_groups = [g for g in WATCHLIST_GROUPS if g != group_name]
            if target_groups:
                target_group = st.selectbox("目标分组", target_groups, key=f"move_target_{group_name}")
                if st.button(f"移动到 {target_group}", key=f"move_btn_{group_name}"):
                    for code in selected_stocks:
                        stock = db.get_watchlist_stock(uid, code, group_name)
                        if stock:
                            db.add_watchlist_stock(uid, stock["code"], stock["name"], target_group, stock["note"],
                                                   stock["alert_up_pct"], stock["alert_down_pct"],
                                                   stock["alert_volume_ratio"], stock["alert_break_price"])
                            db.soft_delete_watchlist_stock(uid, code, group_name)
                    st.success(f"已移动 {len(selected_stocks)} 只股票到 {target_group}")
                    for s in stocks:
                        st.session_state[f"selected_map_{group_name}"][f"chk_{s['code']}_{group_name}"] = False
                    st.rerun()
            else:
                st.info("没有其他分组可移动")
        
        elif action == "复制到":
            target_groups = [g for g in WATCHLIST_GROUPS if g != group_name]
            if target_groups:
                target_group = st.selectbox("目标分组", target_groups, key=f"copy_target_{group_name}")
                if st.button(f"复制到 {target_group}", key=f"copy_btn_{group_name}"):
                    for code in selected_stocks:
                        stock = db.get_watchlist_stock(uid, code, group_name)
                        if stock:
                            db.add_watchlist_stock(uid, stock["code"], stock["name"], target_group, stock["note"],
                                                   stock["alert_up_pct"], stock["alert_down_pct"],
                                                   stock["alert_volume_ratio"], stock["alert_break_price"])
                    st.success(f"已复制 {len(selected_stocks)} 只股票到 {target_group}")
                    st.rerun()
            else:
                st.info("没有其他分组可复制")
        
        elif action == "删除":
            st.warning(f"确定要删除选中的 {len(selected_stocks)} 只股票吗？此操作无法撤销。")
            if st.button(f"确认删除", key=f"del_{group_name}"):
                for code in selected_stocks:
                    db.soft_delete_watchlist_stock(uid, code, group_name)
                st.success(f"已删除 {len(selected_stocks)} 只股票")
                for s in stocks:
                    st.session_state[f"selected_map_{group_name}"][f"chk_{s['code']}_{group_name}"] = False
                st.rerun()
    else:
        st.info("请选择要操作的股票")