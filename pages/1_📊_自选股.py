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

with tab1:
    codes = df["code"].tolist()
    snapshot = latest_for_codes(codes)
    st.dataframe(snapshot, use_container_width=True)

with tab2:
    st.write("完整性检查 (Phase 2: page 6)")

with tab3:
    audit = watchlist_store.get_audit_log(limit=50)
    st.dataframe(audit, use_container_width=True)
