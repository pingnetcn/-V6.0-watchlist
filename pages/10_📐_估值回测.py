"""Page 10: 估值回测 — predict vs actual."""
import streamlit as st
import pandas as pd
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
    st.line_chart(
        df.pivot_table(index="predict_date", columns="horizon_days", values="abs_error_pct")
    )

    st.subheader("方向正确率 (按预测窗口)")
    sign_df = df.groupby("horizon_days")["sign_correct"].mean().reset_index()
    sign_df["sign_correct"] = sign_df["sign_correct"].apply(lambda x: f"{x:.1%}")
    sign_df = sign_df.rename(columns={"horizon_days": "预测窗口(天)", "sign_correct": "方向正确率"})
    st.dataframe(sign_df, width="stretch", height=200, hide_index=True)

    st.subheader("原始回测数据")
    st.caption(f"共 {len(df)} 行")
    height = min(1500, max(300, len(df) * 28 + 60))
    st.dataframe(df, width="stretch", height=height, hide_index=True)
