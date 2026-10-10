"""Page 8: 行业板块 — 行业估值中位 + 多列展示."""
import streamlit as st
from lib.db import industry_benchmark

# Map Chinese column names to user-friendly labels
COLUMN_LABELS = {
    "行业": "行业",
    "公司数": "公司数",
    "PE_TTM中位数": "PE TTM",
    "PB中位数": "PB",
    "ROE中位数_pct": "ROE%",
    "毛利率中位数_pct": "毛利率%",
    "净利率中位数_pct": "净利率%",
    "营收增速中位数_pct": "营收增速%",
    "净利润增速中位数_pct": "净利增速%",
    "资产负债率中位数_pct": "负债率%",
    "经营现金流净利润比中位数": "现金/净利",
}

st.title("🏭 行业板块")

industry = st.text_input("行业名", "白酒")
if industry:
    df = industry_benchmark(industry)
    if df.empty:
        st.warning(f"无「{industry}」行业数据。可试: 白酒 / 银行 / 半导体 / 医药 / 互联网")
    else:
        # Rename columns for display
        display_df = df.rename(columns={c: COLUMN_LABELS.get(c, c) for c in df.columns})
        st.caption(f"行业「{industry}」共 {len(display_df)} 行 (来自主项目 v_industry_benchmark)")
        height = min(1200, max(300, len(display_df) * 28 + 60))
        st.dataframe(display_df, width="stretch", height=height, hide_index=True)
