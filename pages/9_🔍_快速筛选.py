"""Page 9: 快速筛选 — 全市场扫盘."""
import streamlit as st
import pandas as pd
from lib.db import valuation_history_query
from lib.filter_builder import apply, SUGGEST_RELAX
from lib import watchlist_store

st.title("🔍 快速筛选")

with st.sidebar:
    st.subheader("筛选条件")
    margin_gt = st.number_input("安全边际 > %", value=0)
    rating_in = st.multiselect("评级 ∈", ["A+", "A", "B+", "B", "C+", "C", "D"])
    credibility_ge = st.selectbox("可信度 ≥", ["高", "中", "低", "不可信"], index=1)

filters = {}
if margin_gt > 0:
    filters["margin_gt"] = margin_gt
if rating_in:
    filters["rating_in"] = rating_in
if credibility_ge:
    filters["credibility_ge"] = credibility_ge

df = valuation_history_query(limit=1000)
result = apply(df, filters)

if result.empty:
    st.warning(SUGGEST_RELAX(df, filters))
else:
    st.dataframe(result, use_container_width=True)

    # Add to watchlist
    selected = st.multiselect("加入自选股", result["code"].tolist())
    if st.button("➕ 加入") and selected:
        n = watchlist_store.import_codes(selected, source="quick_screener")
        st.success(f"已添加 {n} 只")
