"""Page 5: 买卖推荐 — 资金 → BUY/SELL/HOLD."""
import streamlit as st
from lib.portfolio import rank, format_markdown
from components.portfolio_metrics import render_portfolio_metrics

st.title("🎯 买卖推荐")

cash = st.number_input("总投资 (¥)", value=5_000_000, step=100_000)
top_n = st.slider("Top N", 5, 50, 15)

if st.button("🚀 重算"):
    with st.spinner("计算中..."):
        result = rank(cash_available=cash, top_n=top_n)
    st.session_state["rank_result"] = result

result = st.session_state.get("rank_result")
if result is None:
    st.info("点击 🚀 重算 开始")
    st.stop()

render_portfolio_metrics(result)

for label, key in [("BUY", "buy_list"), ("SELL", "sell_list"), ("HOLD", "hold_list")]:
    with st.expander(f"{label} ({len(result.get(key, []))})"):
        st.dataframe(result.get(key, []), width="stretch")

if st.button("📥 导出 Markdown"):
    md = format_markdown(result)
    st.download_button("下载", md, file_name="portfolio.md", mime="text/markdown")
