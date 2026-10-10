"""Page 3: 跨股对比 — 多股票横向指标."""
import streamlit as st
import pandas as pd
from lib import watchlist_store
from lib.db import latest_for_codes

st.title("⚖️ 跨股对比")

df = watchlist_store.list_all()
if df.empty:
    st.warning("自选股为空")
    st.stop()

codes = st.multiselect(
    "选股 (可多选)",
    df["code"].tolist(),
    default=df["code"].tolist()[:5],
)

if not codes:
    st.info("至少选一只")
    st.stop()

snapshot = latest_for_codes(codes)
# 16 columns per spec §15.1
COLS_ORDER = [
    "code", "name", "current_price", "intrinsic_value", "margin",
    "rating", "credibility", "bull_price_5y", "bear_price_5y",
    "fcff_intrinsic", "pe_intrinsic", "pb_intrinsic", "iv_intrinsic", "ev_intrinsic",
    "failure_modes", "methods_spread",
]
display_cols = [c for c in COLS_ORDER if c in snapshot.columns]
display_df = snapshot[display_cols]

# Column widths
COL_WIDTHS = {
    "code": 70, "name": 110, "current_price": 80, "intrinsic_value": 80,
    "margin": 80, "rating": 60, "credibility": 70,
    "bull_price_5y": 70, "bear_price_5y": 70,
    "fcff_intrinsic": 80, "pe_intrinsic": 80, "pb_intrinsic": 80,
    "iv_intrinsic": 80, "ev_intrinsic": 80,
    "failure_modes": 120, "methods_spread": 90,
}
col_config = {c: st.column_config.Column(c, width=COL_WIDTHS[c]) for c in display_df.columns if c in COL_WIDTHS}

dynamic_height = min(1200, max(300, len(display_df) * 28 + 60))
st.dataframe(
    display_df,
    width="stretch",
    height=dynamic_height,
    hide_index=True,
    column_config=col_config,
)

csv = display_df.to_csv(index=False).encode("utf-8")
st.download_button("📥 导出 CSV", csv, file_name="comparison.csv", mime="text/csv")
