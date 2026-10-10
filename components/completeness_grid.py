"""
Completeness dashboard grid (red/yellow/green matrix).
"""
import streamlit as st
import pandas as pd


TIER_COLORS = {"高": "🟢", "中": "🟡", "低": "🟠", "不可信": "🔴"}
GRADE_COLORS = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "⚫"}


def render_score_one(score: dict):
    cols = st.columns(3)
    cols[0].metric("可信度", f"{TIER_COLORS.get(score.get('credibility_tier', '中'), '❓')} {score.get('credibility_tier')}")
    cols[1].metric("质量评级", f"{GRADE_COLORS.get(score.get('quality_grade', 'C'), '❓')} {score.get('quality_grade')}")
    cols[2].metric("方法分歧", f"{score.get('methods_spread', 0):.1f}%")
    if score.get("failure_modes"):
        st.warning(f"触发失败模式: {', '.join(score['failure_modes'])}")


def render_batch_dashboard(df: pd.DataFrame):
    st.dataframe(df, use_container_width=True)