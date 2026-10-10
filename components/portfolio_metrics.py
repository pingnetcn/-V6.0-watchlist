"""
Portfolio-level KPI cards (5 tiles).
"""
import streamlit as st


def render_portfolio_metrics(result: dict):
    metrics = result.get("portfolio_metrics", {})
    cols = st.columns(5)
    cols[0].metric("BUY 持仓数", metrics.get("buy_count", 0))
    cols[1].metric("行业数", metrics.get("industry_count", 0))
    cols[2].metric("综合分均值", f"{metrics.get('avg_score', 0):.1f}")
    cols[3].metric("预期收益均值", f"{metrics.get('avg_upside', 0):.1f}%")
    cols[4].metric("Top2 集中度", f"{metrics.get('top2_concentration', 0):.1f}%")
