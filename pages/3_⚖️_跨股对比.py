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

codes = st.multiselect("选股 (可多选)", df["code"].tolist(), default=df["code"].tolist()[:5])

if not codes:
    st.info("至少选一只")
    st.stop()

snapshot = latest_for_codes(codes)
# Reorder columns per spec §15.1
COLS_ORDER = ["code", "name", "current_price", "intrinsic_value", "margin",
              "rating", "credibility", "bull_price_5y", "bear_price_5y",
              "fcff_intrinsic", "pe_intrinsic", "pb_intrinsic", "iv_intrinsic", "ev_intrinsic",
              "failure_modes", "methods_spread"]
display_cols = [c for c in COLS_ORDER if c in snapshot.columns]
st.dataframe(snapshot[display_cols], use_container_width=True)

csv = snapshot[display_cols].to_csv(index=False).encode("utf-8")
st.download_button("📥 导出 CSV", csv, file_name="comparison.csv", mime="text/csv")
