"""Watchlist Dashboard — entry point.

Global CSS (max-width 100%, reduced padding, compact dataframe font) applies
to all pages so dataframes fill the page width consistently.
"""
import streamlit as st

st.set_page_config(
    page_title="Watchlist",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Global CSS — applied to all pages
st.markdown(
    "<style>"
    # Remove streamlit's default max-width constraint (was 80% of viewport)
    ".block-container { max-width: 100% !important; padding-top: 1.5rem; "
    "padding-left: 1rem; padding-right: 1rem; padding-bottom: 0rem; }"
    "h1 { margin-bottom: 0.5rem; }"
    # Compact dataframe font + tighter row padding for more visible rows
    "[data-testid='stDataFrame'] { font-size: 0.85rem; }"
    "[data-testid='stDataFrame'] td { padding: 4px 8px !important; }"
    # Tighter tab padding
    ".stTabs [data-baseweb='tab-list'] { gap: 0.5rem; }"
    ".stTabs [data-baseweb='tab'] { padding: 0.5rem 1rem; }"
    "</style>",
    unsafe_allow_html=True,
)

st.title("📊 陈氏鉴股V6.0 Watchlist Dashboard")
st.info("左侧栏选页面 (11 pages) · 点击自选股 tab 看估值快照")
