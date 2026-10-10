"""Page 6: 质量校验 — 单股 + 批量."""
import streamlit as st
from lib import watchlist_store
from lib.completeness import score_one, score_batch, aggregate_dashboard
from lib.valuation_reader import latest_version
from components.completeness_grid import render_score_one, render_batch_dashboard

st.title("✅ 质量校验")

mode = st.radio("模式", ["单股", "批量"], horizontal=True)

if mode == "单股":
    code = st.text_input("股票代码", "000999")
    path = latest_version(code)
    if path is None:
        st.error(f"未找到 {code} 报告")
        st.stop()
    score = score_one(path)
    render_score_one(score)

elif mode == "批量":
    codes = watchlist_store.list_all()["code"].tolist()
    df = score_batch(codes)
    if df.empty:
        st.info("自选股为空")
        st.stop()
    agg = aggregate_dashboard(codes)
    cols = st.columns(3)
    for tier, count in agg["tier_distribution"].items():
        cols[0].metric(f"可信度 {tier}", count)
    st.write("Top 失败模式:", agg["top_failure_modes"])
    render_batch_dashboard(df)
