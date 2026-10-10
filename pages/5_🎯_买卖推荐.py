"""Page 5: 买卖推荐 — 资金 → BUY/SELL/HOLD."""
import streamlit as st
from lib.portfolio import rank, format_markdown
from components.portfolio_metrics import render_portfolio_metrics

st.title("🎯 买卖推荐")

cash = st.number_input("总投资 (¥)", value=5_000_000, step=100_000)
top_n = st.slider("Top N", 5, 50, 15)

source = st.radio(
    "数据源",
    ["md (E:/stock/Val 文件报告)", "kb (主项目 kb.db)"],
    index=0,
    horizontal=True,
    help="md: 读文件系统 val_*.txt 报告; kb: 读主项目 kb.db",
)

if st.button("🚀 重算"):
    with st.spinner("计算中..."):
        try:
            src = "md" if source.startswith("md") else "kb"
            result = rank(cash_available=cash, top_n=top_n, source=src)
        except Exception as e:
            st.error(f"rank() 失败: {e}")
            st.info("fallback: 用本地 rank_local()")
            from lib.portfolio_local import rank_local
            result = rank_local(cash_available=cash, top_n=top_n)
    st.session_state["rank_result"] = result

result = st.session_state.get("rank_result")
if result is None:
    st.info("点击 🚀 重算 开始")
    st.stop()

render_portfolio_metrics(result)

import pandas as pd
for label, key in [("BUY", "buy_list"), ("SELL", "sell_list"), ("HOLD", "hold_list")]:
    items = result.get(key, [])
    with st.expander(f"{label} ({len(items)})"):
        if items:
            st.dataframe(pd.DataFrame(items), width="stretch", height=400, hide_index=True)
        else:
            st.info(f"无 {label}")

if st.button("📥 导出 Markdown"):
    try:
        md = format_markdown(result)
    except Exception:
        md = "# Portfolio\n\n"
        for label, key in [("BUY", "buy_list"), ("SELL", "sell_list"), ("HOLD", "hold_list")]:
            items = result.get(key, [])
            md += f"## {label} ({len(items)})\n\n"
            for h in items:
                md += f"- {h.get('code', '?')} {h.get('name', '')} score={h.get('composite_score', 0):.0f}\n"
    st.download_button("下载", md, file_name="portfolio.md", mime="text/markdown")
