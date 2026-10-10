"""Page 7: 投资组合 — 持仓 + 调仓."""
import streamlit as st
import pandas as pd
from lib.portfolio import rank

st.title("💼 投资组合")

# Cache rank() result in session_state, auto-compute on first load
if "portfolio_rebalance" not in st.session_state:
    with st.spinner("计算调仓中..."):
        try:
            st.session_state["portfolio_rebalance"] = rank(cash_available=5_000_000, top_n=15)
        except Exception as e:
            st.error(f"rank() 失败: {e}")
            st.info("fallback: 用本地 rank_local()")
            from lib.portfolio_local import rank_local
            st.session_state["portfolio_rebalance"] = rank_local(cash_available=5_000_000, top_n=15)

result = st.session_state["portfolio_rebalance"]

st.subheader("当前持仓")
holdings = st.data_editor(
    pd.DataFrame(columns=["code", "shares", "cost"]),
    num_rows="dynamic",
    width="stretch",
    height=200,
)

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    cash = st.number_input("可投金额", value=5_000_000, step=100_000, key="cash_input")
with col2:
    top_n = st.number_input("Top N", min_value=5, max_value=50, value=15, step=5, key="topn_input")
with col3:
    refresh = st.button("🚀 重算")

if refresh:
    with st.spinner("重算中..."):
        try:
            st.session_state["portfolio_rebalance"] = rank(
                cash_available=cash, top_n=top_n, source="md"
            )
        except Exception as e:
            from lib.portfolio_local import rank_local
            st.session_state["portfolio_rebalance"] = rank_local(
                cash_available=cash, top_n=top_n
            )
    st.rerun()

# Show rebalance suggestions
if result and result.get("buy_list"):
    st.subheader(f"调仓建议 — BUY {len(result['buy_list'])} 只")

    buy_df = pd.DataFrame(result["buy_list"])
    height = min(1500, max(300, len(buy_df) * 28 + 60))
    st.dataframe(buy_df, width="stretch", height=height, hide_index=True)

    # Sector allocation
    if result.get("sector_allocation"):
        st.subheader("行业分布")
        sector_df = pd.DataFrame([
            {"行业": k, "权重": f"{v:.1%}"}
            for k, v in sorted(result["sector_allocation"].items(), key=lambda x: -x[1])
        ])
        st.dataframe(sector_df, width="stretch", height=300, hide_index=True)
elif result:
    st.info("无可信标的 (no BUY recommendations)")

# Risk warnings
if result and result.get("risk_warnings"):
    for w in result["risk_warnings"]:
        st.warning(w)
