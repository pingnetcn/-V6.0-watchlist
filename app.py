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

# Global CSS via st.html() — renders in <body>, more reliable than st.markdown()
# for ensuring styles apply on initial page load + browser refresh.
# Triple-redundant targeting (data-testid, class, body) so even browser cache
# without our CSS still gets full-width via the width="stretch" on dataframes.
st.html(
    """
    <style>
    /* === Force full width container (overrides streamlit default 80% cap) === */
    html, body { width: 100% !important; min-width: 100vw !important; }
    .block-container,
    [data-testid="stAppViewContainer"] .main .block-container,
    section.main .block-container {
        max-width: 100vw !important;
        min-width: 100vw !important;
        width: 100vw !important;
        padding-top: 1.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
        padding-bottom: 0rem;
    }
    h1 { margin-bottom: 0.5rem; }

    /* === Streamlit main section also full width === */
    [data-testid="stAppViewContainer"] > section,
    [data-testid="stAppViewContainer"] > section > div {
        max-width: 100vw !important;
        width: 100% !important;
    }

    /* === DataFrame fills its container === */
    [data-testid="stDataFrame"],
    [data-testid="stDataFrame"] > div,
    [data-testid="stDataFrame"] iframe {
        width: 100% !important;
        min-width: 100% !important;
    }

    /* === Compact dataframe font + tighter row padding === */
    [data-testid="stDataFrame"] { font-size: 0.85rem; }
    [data-testid="stDataFrame"] td { padding: 4px 8px !important; }

    /* === Tighter tab padding === */
    .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
    .stTabs [data-baseweb="tab"] { padding: 0.5rem 1rem; }

    /* === Hide dev "Deploy" button === */
    [data-testid="stToolbar"] { display: none !important; }
    </style>
    """
)

st.title("📊 陈氏鉴股V6.0 Watchlist Dashboard")
st.info("左侧栏选页面 (11 pages) · 点击自选股 tab 看估值快照")
