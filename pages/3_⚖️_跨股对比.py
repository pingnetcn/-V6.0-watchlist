"""Page 3: 跨股对比 — 多股票横向指标."""
import streamlit as st
import pandas as pd
from lib import watchlist_store
from lib.db import latest_for_codes
from lib.ui_helpers import build_stock_options, stock_name_map

st.title("⚖️ 跨股对比")

df = watchlist_store.list_all()
if df.empty:
    st.warning("自选股为空")
    st.stop()

codes = df["code"].tolist()
options = build_stock_options(codes, stock_name_map(codes))
labels = [l for l, _ in options]
values = [v for _, v in options]

# Try to get buy list from portfolio.rank(); fall back to first 5 on failure
default_codes = codes[:5]
try:
    from lib.portfolio import rank
    rank_result = rank(cash_available=5_000_000, top_n=15)
    buy_list = rank_result.get("buy_list", [])
    if isinstance(buy_list, list) and buy_list:
        # Extract codes from buy list (might be dicts with 'code' field)
        buy_codes = []
        for item in buy_list:
            code = item.get("code") if isinstance(item, dict) else None
            if code:
                buy_codes.append(str(code))
        # Intersect with watchlist (only show watchlist stocks)
        buy_codes_in_wl = [c for c in buy_codes if c in codes]
        if buy_codes_in_wl:
            default_codes = buy_codes_in_wl[:15]
            st.caption(f"💡 默认选中 portfolio rank() 的 BUY list ({len(default_codes)} 只)。可在下面修改。")
except Exception as e:
    st.caption(f"⚠️ portfolio.rank() 失败,默认前 5 只 ({e})")

# Build default labels for multiselect
default_labels = [l for l, v in options if v in default_codes]

selected_labels = st.multiselect(
    "选股 (按名称排序,可多选)",
    labels,
    default=default_labels if default_labels else labels[:5],
)

selected_codes = [values[labels.index(l)] for l in selected_labels]

if not selected_codes:
    st.info("至少选一只")
    st.stop()

snapshot = latest_for_codes(selected_codes)
# 16 columns per spec §15.1 (excluding failure_modes — replaced by methods_spread for less noise)
COLS_ORDER = [
    "code", "name", "current_price", "intrinsic_value", "margin",
    "rating", "credibility", "bull_price_5y", "bear_price_5y",
    "fcff_intrinsic", "pe_intrinsic", "pb_intrinsic", "iv_intrinsic", "ev_intrinsic",
    "methods_spread",
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
    "methods_spread": 90,
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
