"""
Plotly historical valuation timeline chart.
"""
import plotly.graph_objects as go
import streamlit as st
import pandas as pd


def render_single_stock_timeline(code: str, df: pd.DataFrame):
    if df.empty:
        st.warning("无历史数据")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["valuation_date"], y=df["intrinsic_value"], name="评估价", line=dict(color="gold")))
    fig.add_trace(go.Scatter(x=df["valuation_date"], y=df["current_price"], name="现价", line=dict(color="cyan")))
    fig.add_trace(go.Scatter(x=df["valuation_date"], y=df["bull_price_5y"], name="5y 牛", line=dict(color="lightgreen", dash="dot")))
    fig.add_trace(go.Scatter(x=df["valuation_date"], y=df["bear_price_5y"], name="5y 熊", line=dict(color="salmon", dash="dot")))
    fig.update_layout(title=f"{code} 估值历史", xaxis_title="日期", yaxis_title="价格")
    st.plotly_chart(fig, use_container_width=True)


def render_compare_timeline(codes: list[str], df: pd.DataFrame):
    """Multi-stock timeline: one line per code, intrinsic_value over time."""
    if df.empty or not codes:
        st.warning("无数据")
        return
    fig = go.Figure()
    palette = ["gold", "cyan", "lightgreen", "salmon", "violet", "orange"]
    for i, code in enumerate(codes):
        sub = df[df["code"] == code].sort_values("valuation_date")
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["valuation_date"],
            y=sub["intrinsic_value"],
            name=code,
            line=dict(color=palette[i % len(palette)]),
        ))
    fig.update_layout(title=f"多股评估价对比 ({len(codes)} 只)", xaxis_title="日期", yaxis_title="评估价")
    st.plotly_chart(fig, use_container_width=True)