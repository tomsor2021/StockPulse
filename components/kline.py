"""K线图组件（Plotly candlestick + 均线 + 成交量）"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def kline_chart(df, theme="浅色", ma_periods=(5, 10, 20)):
    if df is None or df.empty:
        return None
    df = df.sort_values("date").tail(120)
    ma_colors = {5: "#FF9800", 10: "#2196F3", 20: "#9C27B0"}
    for p in ma_periods:
        df[f"MA{p}"] = df["close"].rolling(window=p).mean()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df["date"], open=df["open"], high=df["high"],
                                  low=df["low"], close=df["close"], name="K线",
                                  increasing_line_color="#D32F2F", decreasing_line_color="#2E7D32"), row=1, col=1)
    for p in ma_periods:
        if f"MA{p}" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df[f"MA{p}"], line=dict(color=ma_colors[p], width=1), name=f"MA{p}"), row=1, col=1)
    colors = ["#D32F2F" if r["close"] >= r["open"] else "#2E7D32" for _, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df["date"], y=df["volume"], name="成交量", marker_color=colors), row=2, col=1)
    fig.update_layout(title="日K线图", height=500, margin=dict(l=20, r=20, t=40, b=20),
                       xaxis_rangeslider_visible=False, showlegend=True, hovermode="x unified")
    return fig


def weekly_kline_chart(df, theme="浅色"):
    if df is None or df.empty:
        return None
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    weekly = df.resample("W", on="date").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    return kline_chart(weekly.reset_index(), theme)
