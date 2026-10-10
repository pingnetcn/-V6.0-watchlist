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
st.html(
    """
    <style>
    /* Force full width container (overrides streamlit default 80% cap) */
    .block-container {
        max-width: 100% !important;
        min-width: 100% !important;
        width: 100% !important;
        padding-top: 1.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
        padding-bottom: 0rem;
    }
    h1 { margin-bottom: 0.5rem; }

    /* DataFrame fills its container */
    [data-testid="stDataFrame"] { width: 100% !important; }
    [data-testid="stDataFrame"] > div { width: 100% !important; }
    [data-testid="stDataFrame"] iframe { width: 100% !important; }

    /* Compact dataframe font + tighter row padding */
    [data-testid="stDataFrame"] { font-size: 0.85rem; }
    [data-testid="stDataFrame"] td { padding: 4px 8px !important; }

    /* Tighter tab padding */
    .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
    .stTabs [data-baseweb="tab"] { padding: 0.5rem 1rem; }

    /* Hide dev "Deploy" button */
    [data-testid="stToolbar"] { display: none !important; }

    /* Make sure main area expands (not constrained by sidebar) */
    [data-testid="stAppViewContainer"] > section { width: 100% !important; }
    [data-testid="stAppViewContainer"] > section > div { width: 100% !important; }
    </style>
    """
)

st.title("📊 陈氏鉴股V6.0 Watchlist Dashboard")
st.info("左侧栏选页面 (11 pages) · 点击自选股 tab 看估值快照")
