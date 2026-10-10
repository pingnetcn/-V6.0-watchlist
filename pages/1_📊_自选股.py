"""Page 1: 自选股首页 — CRUD + 估值快照."""
import streamlit as st
from lib import watchlist_store
from lib.db import latest_for_codes
from components.sidebar_watchlist import render_sidebar

render_sidebar()
st.title("📊 自选股")

tab1, tab2, tab3 = st.tabs(["估值快照", "完整性", "调整记录"])

df = watchlist_store.list_all()
if df.empty:
    st.info("📥 自选股为空。可在侧栏添加,或运行 scripts/import_candidate_pool.py")
    st.stop()

# Pick 10 most useful columns (drop id, redundant metadata)
DISPLAY_COLS = [
    "code", "name", "industry", "valuation_date",
    "current_price", "intrinsic_value", "margin", "rating",
    "credibility", "bull_price_5y",
]
COLUMN_LABELS = {
    "code": "代码", "name": "名称", "industry": "行业",
    "valuation_date": "估值日期", "current_price": "现价",
    "intrinsic_value": "评估价", "margin": "安全边际%",
    "rating": "评级", "credibility": "可信度",
    "bull_price_5y": "5y牛",
}

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

    # Format margin as percent string (for visual clarity)
    if "安全边际%" in display_df.columns:
        display_df["安全边际%"] = display_df["安全边际%"].apply(
            lambda x: f"{x:+.1f}%" if pd_notnull(x) else ""
        )
    # Format price columns
    for col in ["现价", "评估价", "5y牛"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda x: f"{x:.2f}" if pd_notnull(x) else ""
            )

    st.caption(f"共 {len(display_df)} 只股票 · 按 valuation_date 降序")
    st.dataframe(
        display_df,
        use_container_width=True,
        height=800,  # fills most of viewport
        hide_index=True,
    )

with tab2:
    st.write("完整性检查 (Phase 2: page 6)")

with tab3:
    audit = watchlist_store.get_audit_log(limit=50)
    st.dataframe(audit, use_container_width=True, height=600, hide_index=True)


def pd_notnull(x):
    """Helper: check if value is not null/NaN (avoids importing pandas at top)."""
    try:
        import math
        if x is None:
            return False
        if isinstance(x, float) and math.isnan(x):
            return False
        return True
    except Exception:
        return True
