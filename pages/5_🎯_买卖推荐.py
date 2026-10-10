"""Page 5: 买卖推荐 — 资金 → BUY/SELL/HOLD."""
import streamlit as st
import pandas as pd
from lib.portfolio_local import rank_local


def render_portfolio_metrics(result):
    """5 KPI tiles + sector table per spec §6.5."""
    metrics = result.get("portfolio_metrics", {})
    cols = st.columns(5)
    cols[0].metric("BUY 持仓数", metrics.get("buy_count", 0))
    cols[1].metric("行业数", len(result.get("sector_allocation", {})))
    cols[2].metric("综合分均值", f"{metrics.get('avg_score', 0):.1f}")
    cols[3].metric("预期收益均值", f"{metrics.get('avg_margin', 0):.1f}%")
    cols[4].metric("Top2 集中度", f"{metrics.get('top2_concentration', 0):.1%}")

    if result.get("risk_warnings"):
        for w in result["risk_warnings"]:
            st.warning(w)

    if result.get("sector_allocation"):
        st.subheader("行业分布")
        sector_df = pd.DataFrame([
            {"行业": k, "权重": f"{v:.1%}"}
            for k, v in sorted(result["sector_allocation"].items(), key=lambda x: -x[1])
        ])
        st.dataframe(sector_df, width="stretch", height=300, hide_index=True)


st.title("🎯 买卖推荐")

cash = st.number_input("总投资 (¥)", value=5_000_000, step=100_000)
top_n = st.slider("Top N", 5, 50, 15)

if st.button("🚀 重算"):
    with st.spinner("计算中..."):
        result = rank_local(cash_available=cash, top_n=top_n)
    st.session_state["rank_result"] = result

result = st.session_state.get("rank_result")
if result is None:
    st.info("点击 🚀 重算 开始")
    st.stop()

render_portfolio_metrics(result)

for label, key in [("BUY", "buy_list"), ("SELL", "sell_list"), ("HOLD", "hold_list")]:
    items = result.get(key, [])
    with st.expander(f"{label} ({len(items)})"):
        if items:
            st.dataframe(pd.DataFrame(items), width="stretch", height=400, hide_index=True)
        else:
            st.info(f"无 {label}")

if st.button("📥 导出 Markdown"):
    md = "# Portfolio\n\n"
    for label, key in [("BUY", "buy_list"), ("SELL", "sell_list"), ("HOLD", "hold_list")]:
        items = result.get(key, [])
        md += f"## {label} ({len(items)})\n\n"
        for h in items:
            md += f"- {h.get('code', '?')} {h.get('name', '')} score={h.get('composite_score', 0):.0f}\n"
    st.download_button("下载", md, file_name="portfolio.md", mime="text/markdown")
