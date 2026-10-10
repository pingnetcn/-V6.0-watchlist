"""Page 1: 自选股首页 — CRUD + 估值快照."""
import math
import streamlit as st
import pandas as pd
from lib import watchlist_store
from lib.db import latest_for_codes
from components.sidebar_watchlist import render_sidebar


def _fmt_pct(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    return f"{x:+.1f}%"


def _fmt_price(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    return f"{x:.2f}"


# Per-column formatters
FORMATTERS = {
    "安全边际%": _fmt_pct,
    "方法分歧%": _fmt_pct,
    "30%买入距%": _fmt_pct,
    "现价": _fmt_price,
    "评估价": _fmt_price,
    "5y牛": _fmt_price,
    "5y熊": _fmt_price,
    "5y加权": _fmt_price,
}


# 14 columns: 估值核心 + 风险信号 + 行动信号 (失败模式被方法分歧替代 — 类似信息,避免冗余)
DISPLAY_COLS = [
    "code", "name", "industry", "valuation_date",
    "current_price", "intrinsic_value", "margin", "rating",
    "credibility", "main_method", "methods_spread",
    "bull_price_5y", "bear_price_5y", "weighted_5y",
    "dist_to_buy_30",
]
COLUMN_LABELS = {
    "code": "代码", "name": "名称", "industry": "行业",
    "valuation_date": "估值日期", "current_price": "现价",
    "intrinsic_value": "评估价", "margin": "安全边际%",
    "rating": "评级", "credibility": "可信度",
    "main_method": "主推方法", "methods_spread": "方法分歧%",
    "bull_price_5y": "5y牛", "bear_price_5y": "5y熊",
    "weighted_5y": "5y加权", "dist_to_buy_30": "30%买入距%",
}

# Column widths in pixels (total target ~ 1400-1800 for 15 cols on wide screen)
COL_WIDTHS = {
    "代码": 70, "名称": 110, "行业": 110, "估值日期": 110,
    "现价": 70, "评估价": 80, "安全边际%": 80, "评级": 60,
    "可信度": 70, "主推方法": 110, "方法分歧%": 75,
    "5y牛": 70, "5y熊": 70, "5y加权": 70,
    "30%买入距%": 90, "失败模式": 100,
}

render_sidebar()
st.title("📊 自选股")

tab1, tab2, tab3 = st.tabs(["估值快照", "完整性", "调整记录"])

df = watchlist_store.list_all()
if df.empty:
    st.info("📥 自选股为空。可在侧栏添加,或运行 scripts/import_candidate_pool.py")
    st.stop()

with tab1:
    codes = df["code"].tolist()
    try:
        snapshot = latest_for_codes(codes)
    except RuntimeError as e:
        st.error(f"⚠️ DuckDB 暂时被主项目 (8905) 占用。{e}")
        st.info("请稍候刷新 (Ctrl+R) — 通常几秒后主项目写完就释放锁。")
        st.stop()

    # Select + rename columns
    display_df = snapshot[[c for c in DISPLAY_COLS if c in snapshot.columns]].copy()
    display_df = display_df.rename(columns=COLUMN_LABELS)

    # Sort selector
    sort_options = {
        "安全边际% (降序)": ("margin", False),
        "安全边际% (升序)": ("margin", True),
        "评估价 (降序)": ("intrinsic_value", False),
        "现价 (降序)": ("current_price", False),
        "5y加权 (降序)": ("weighted_5y", False),
        "30%买入距% (降序)": ("dist_to_buy_30", False),
        "估值日期 (降序)": ("valuation_date", False),
    }
    sort_label = st.selectbox(
        "排序", list(sort_options.keys()),
        index=0, label_visibility="collapsed"
    )
    sort_col, ascending = sort_options[sort_label]
    sort_col_label = COLUMN_LABELS.get(sort_col, sort_col)
    if sort_col_label in display_df.columns:
        sort_raw = pd.to_numeric(display_df[sort_col_label], errors="coerce")
        display_df = display_df.assign(_sort_key=sort_raw).sort_values(
            "_sort_key", ascending=ascending, na_position="last"
        ).drop(columns=["_sort_key"])

    # Apply per-column formatters
    for col, fmt in FORMATTERS.items():
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(fmt)

    # Build column_config for explicit widths (so the table fills the page)
    col_config = {
        label: st.column_config.Column(label, width=width)
        for label, width in COL_WIDTHS.items()
        if label in display_df.columns
    }

    st.caption(f"共 {len(display_df)} 只股票 · 按 valuation_date 降序")
    dynamic_height = min(1500, max(400, len(display_df) * 28 + 60))
    st.dataframe(
        display_df,
        width="stretch",
        height=dynamic_height,
        hide_index=True,
        column_config=col_config,
    )

with tab2:
    st.write("完整性检查 (Phase 2: page 6)")

with tab3:
    audit = watchlist_store.get_audit_log(limit=50)
    st.dataframe(audit, width="stretch", height=600, hide_index=True)
