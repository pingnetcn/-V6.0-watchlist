"""Page 8: 行业板块 — 行业估值中位."""
import streamlit as st
from lib.db import industry_benchmark

st.title("🏭 行业板块")

industry = st.text_input("行业名", "白酒")
if industry:
    df = industry_benchmark(industry)
    if df.empty:
        st.warning("无数据")
    else:
        height = min(1200, max(300, len(df) * 28 + 60))
        st.dataframe(df, use_container_width=True, height=height, hide_index=True)
