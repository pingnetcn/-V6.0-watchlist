"""Page 7: 投资组合 — 持仓 + 调仓."""
import streamlit as st
import pandas as pd
from lib.portfolio import rank
from lib.pm_kelly_wrap import compute_kelly_preview

st.title("💼 投资组合")

st.subheader("当前持仓")
holdings = st.data_editor(
    pd.DataFrame(columns=["code", "shares", "cost"]),
    num_rows="dynamic",
    use_container_width=True,
    height=300,
)

cash = st.number_input("可投金额", value=5_000_000, step=100_000)

if st.button("🚀 计算调仓"):
    result = rank(cash_available=cash, top_n=15)
    st.session_state["rebalance"] = result

result = st.session_state.get("rebalance")
if result:
    st.subheader("调仓建议")
    buy_list = result.get("buy_list", [])
    if isinstance(buy_list, list) and buy_list:
        buy_df = pd.DataFrame(buy_list)
        height = min(1200, max(300, len(buy_df) * 28 + 60))
        st.dataframe(buy_df, use_container_width=True, height=height, hide_index=True)
    else:
        st.dataframe(buy_list, use_container_width=True, height=400, hide_index=True)

    st.subheader("凯利公式预览")
    for holding in result.get("buy_list", [])[:5]:
        kelly = compute_kelly_preview(holding)
        st.write(
            f"{holding.get('code', '?')}: position% = {kelly.get('position_pct', 0):.1f}%"
        )
