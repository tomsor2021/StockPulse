"""自选股池页面"""
import streamlit as st
import streamlit.components.v1 as components
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

    # 获取各组股票数量
    all_stocks = db.get_watchlist(uid)
    group_counts = {}
    for s in all_stocks:
        g = s["group_name"]
        group_counts[g] = group_counts.get(g, 0) + 1

    tabs = st.tabs([f"{g} ({group_counts.get(g, 0)})" for g in WATCHLIST_GROUPS])
    for idx, group in enumerate(WATCHLIST_GROUPS):
        with tabs[idx]:
            _render_group(uid, group)


def _render_group(uid, group_name):
    # 添加自选股
    with st.expander("➕ 添加自选股", expanded=False):
        # ── JS桥接：components.html 使用 setComponentValue 传值 ──
        # 首次运行返回 DeltaGenerator，JS 调用 setComponentValue 触发 rerun 后，
        # 下一次运行 components.html 应返回 JS 传来的字符串值
        _rt = components.html(
            f"""
            <script>
            (function() {{
                var findInput = function() {{
                    var inp = window.parent.document.querySelector('input[placeholder*="000001"]');
                    if (inp && !inp._sw) {{
                        inp._sw = true;
                        inp.addEventListener('input', function() {{
                            var digits = this.value.replace(/\\D/g, '');
                            if (digits.length >= 5) {{
                                try {{ Streamlit.setComponentValue(this.value); }} catch(e) {{}}
                            }}
                        }});
                    }}
                }};
                findInput();
                new MutationObserver(findInput).observe(window.parent.document.body, {{
                    childList: true, subtree: true
                }});
            }})();
            </script>
            """,
            height=0,
        )
        # 如果 JS 传回了值，同步到 session_state 以便 text_input 显示
        if isinstance(_rt, str):
            st.session_state[f"add_code_{group_name}"] = _rt
        
        raw_code = st.session_state.get(f"add_code_{group_name}", "") or ""
        parsed_code = parse_stock_code(raw_code.strip()) if raw_code.strip() else ""
        
        stock_name = None
        if len(parsed_code) in (5, 6):
            stock_name = fetcher.fetch_stock_name(parsed_code)
        
        col_code, col_name, col_note = st.columns([1.5, 2, 1.5])
        with col_code:
            code_input = st.text_input("股票/基金代码", placeholder="例如 A股 000001 / 港股 06869 / 基金 510300",
                                       key=f"add_code_{group_name}")
        
        with col_name:
            if stock_name:
                st.markdown(f"<div style='margin-top:25px'><span style='color:#4CAF50;font-weight:600;font-size:15px'>📌 {stock_name}</span></div>", unsafe_allow_html=True)
            elif len(parsed_code) in (5, 6):
                st.markdown(f"<div style='margin-top:25px'><span style='color:#9E9E9E'>❓ 未查询到名称</span></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='margin-top:25px'><span style='color:#BDBDBD;font-size:13px'>输入代码后自动显示名称</span></div>", unsafe_allow_html=True)
        
        with col_note:
            note_input = st.text_input("备注（选填）", key=f"add_note_{group_name}")
        
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

    # 构建DataFrame用于st.dataframe展示
    df_data = []
    for s in stocks:
        d = daily_dict.get(s["code"], {})
        change = d.get("change_pct")
        change_val = float(change) if change else None
        df_data.append({
            "代码": s["code"],
            "名称": s["name"] or "-",
            "现价": d.get("close_price", 0),
            "涨跌幅": change_val,
            "备注": s["note"] or "-"
        })
    
    df = pd.DataFrame(df_data)
    
    # 使用pandas Styler对涨跌幅列着色
    def color_change(val):
        if val is None:
            return ""
        if val > 0:
            return "color: #D32F2F; font-weight: 500;"
        elif val < 0:
            return "color: #2E7D32; font-weight: 500;"
        else:
            return ""
    
    styled_df = df.style.map(color_change, subset=["涨跌幅"])
    
    # 使用st.dataframe原生行选择功能
    selection = st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key=f"watchlist_table_{group_name}",
        column_config={
            "代码": st.column_config.TextColumn("代码", width="small"),
            "名称": st.column_config.TextColumn("名称", width="medium"),
            "现价": st.column_config.NumberColumn("现价", format="%.2f", width="small"),
            "涨跌幅": st.column_config.NumberColumn("涨跌幅", format="%.2f%%", width="small"),
            "备注": st.column_config.TextColumn("备注", width="medium"),
        }
    )
    
    # 获取选中的股票代码
    selected_indices = selection.selection.rows
    selected_stocks = [stocks[i]["code"] for i in selected_indices]
    
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
                st.rerun()
    else:
        st.info("请选择要操作的股票")