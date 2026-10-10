"""
Sidebar with watchlist CRUD + global navigation.
"""
import streamlit as st
from lib import watchlist_store


def render_sidebar():
    st.sidebar.header("📊 自选股")
    new_code = st.sidebar.text_input("➕ 添加股票代码", key="add_stock_input")
    if st.sidebar.button("添加"):
        if new_code.strip():
            if watchlist_store.add(new_code.strip()):
                st.sidebar.success(f"已添加 {new_code}")
                st.cache_resource.clear()
            else:
                st.sidebar.error("添加失败")

    df = watchlist_store.list_all()
    if not df.empty:
        st.sidebar.dataframe(
            df[["code", "note"]].fillna(""),
            hide_index=True,
            use_container_width=True,
        )
        to_remove = st.sidebar.selectbox("➖ 删除", [""] + df["code"].tolist())
        if st.sidebar.button("删除选中") and to_remove:
            if watchlist_store.remove(to_remove):
                st.sidebar.success(f"已删除 {to_remove}")
                st.cache_resource.clear()

    if st.sidebar.button("📥 导入候选池"):
        # Will be wired up by Task 7 (page 1)
        st.sidebar.info("见 page 1")
