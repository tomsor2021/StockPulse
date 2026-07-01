"""看板卡片组件"""
import streamlit as st
from config.theme import color_change, arrow_change
from utils.helpers import format_pct, format_money, format_volume


def market_index_card(title, value, change_pct, volume, colors):
    change_str = format_pct(change_pct)
    vol_str = format_volume(volume)
    clr = color_change(change_pct, colors)
    arrow = arrow_change(change_pct)
    st.markdown(f"""
    <div style='background:{colors["card_bg"]};padding:16px;border-radius:8px;margin:4px 0'>
        <div style='font-size:14px;color:{colors["text_secondary"]}'>{title}</div>
        <div style='font-size:24px;font-weight:bold;color:{clr}'>{arrow} {change_str}</div>
        <div style='font-size:12px;color:{colors["text_secondary"]}'>成交额: {vol_str}</div>
    </div>
    """, unsafe_allow_html=True)


def stat_card(label, value, sub_text="", color=None):
    if color is None:
        color = "#212121"
    st.markdown(f"""
    <div style='background:{st.get_option("theme.secondaryBackgroundColor")};padding:14px;border-radius:8px;margin:4px 0'>
        <div style='font-size:13px;color:#757575'>{label}</div>
        <div style='font-size:22px;font-weight:bold;color:{color}'>{value}</div>
        {f'<div style="font-size:11px;color:#9E9E9E">{sub_text}</div>' if sub_text else ''}
    </div>
    """, unsafe_allow_html=True)


def alert_item(stock_name, alert_type, message, alert_id, user_id, on_read):
    type_labels = {"up_limit":"📈涨停","down_limit":"📉跌停","volume_spike":"📊放量","price_break":"🔻破位","custom":"📌"}
    label = type_labels.get(alert_type, "📌")
    cols = st.columns([3, 1, 1])
    with cols[0]:
        st.markdown(f"**{stock_name}** {label} {message}")
    with cols[2]:
        if st.button("已读", key=f"alert_{alert_id}"):
            on_read(alert_id, user_id)
            st.rerun()
