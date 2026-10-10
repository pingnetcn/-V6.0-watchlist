"""Page 4: 历史时序 — 同股跨期 / 全市场快照."""
import streamlit as st
from datetime import date, timedelta
from lib.history_query import show_stock, show_date, show_compare
from components.history_chart import render_single_stock_timeline

st.title("📅 历史时序")

mode = st.radio("模式", ["单股", "单日", "同股diff"], horizontal=True)

if mode == "单股":
    code = st.text_input("股票代码", "000999")
    if code:
        df = show_stock(code)
        render_single_stock_timeline(code, df)

elif mode == "单日":
    target = st.date_input("日期", date.today() - timedelta(days=1))
    df = show_date(target)
    if not df.empty:
        height = min(1500, max(300, len(df) * 28 + 60))
        st.dataframe(df, use_container_width=True, height=height, hide_index=True)
    else:
        st.info("该日期无数据")

elif mode == "同股diff":
    code = st.text_input("股票代码", "000999", key="diff_code")
    if code:
        result = show_compare(code)
        if result.get("first") is None:
            st.warning("历史不足 2 行")
        else:
            st.json(result["diff"])
