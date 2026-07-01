"""Plotly 图表封装"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from config.theme import get_theme_color


def pie_chart(labels, values, title="", theme="浅色"):
    colors = get_theme_color(theme)
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
    fig.update_layout(
        title=title, height=300, margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor=colors["bg"], font_color=colors["text"],
        showlegend=True, legend=dict(orientation="h", y=-0.1),
    )
    return fig


def line_chart(df, x_col, y_col, title="", color="#1976D2", theme="浅色"):
    colors = get_theme_color(theme)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col], mode="lines+markers",
                              line=dict(color=color, width=2), name=y_col))
    fig.update_layout(
        title=title, height=300, margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor=colors["bg"], plot_bgcolor=colors["bg"],
        font_color=colors["text"], xaxis_title=None, yaxis_title=None,
    )
    return fig


def bar_chart(df, x_col, y_col, title="", color="#1976D2", theme="浅色"):
    colors = get_theme_color(theme)
    fig = px.bar(df, x=x_col, y=y_col, title=title, color_discrete_sequence=[color])
    fig.update_layout(
        height=300, margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor=colors["bg"], plot_bgcolor=colors["bg"],
        font_color=colors["text"],
    )
    return fig


def area_chart(df, x_col, y_col, title="", up_color="#D32F2F", down_color="#2E7D32", theme="浅色"):
    colors = get_theme_color(theme)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x_col], y=df[y_col], fill="tozeroy", mode="lines",
        line=dict(color=up_color, width=2),
        fillcolor=up_color,
    ))
    fig.update_layout(
        title=title, height=250, margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor=colors["bg"], plot_bgcolor=colors["bg"],
        font_color=colors["text"], showlegend=False,
    )
    return fig


def calendar_heatmap(dates_df, date_col="date", value_col="value", title=""):
    if dates_df.empty:
        return None
    fig = px.density_heatmap(
        dates_df, x=pd.to_datetime(dates_df[date_col]).dt.month,
        y=pd.to_datetime(dates_df[date_col]).dt.day,
        z=value_col, title=title,
    )
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    return fig
