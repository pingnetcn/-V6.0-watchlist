"""Page 10: 估值回测 — predict vs actual."""
import streamlit as st
from lib.history_query import compute_valuation_accuracy

st.title("📐 估值回测")

code = st.text_input("股票代码", "000999")

df = compute_valuation_accuracy(code, horizons_days=[30, 90, 180, 365])

if df.empty:
    st.warning("历史不足")
elif len(df) < 5:
    st.warning(f"样本不足 ({len(df)} 行),< 5 警告,< 3 不可回测")
elif len(df) < 3:
    st.error(f"样本严重不足 ({len(df)} 行),无法回测")
else:
    st.line_chart(df.pivot_table(index="predict_date", columns="horizon_days", values="abs_error_pct"))
    st.write("Sign correct rate:", df.groupby("horizon_days")["sign_correct"].mean())