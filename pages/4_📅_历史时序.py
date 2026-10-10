"""Page 4: 历史时序 — 同股跨期 / 全市场快照."""
import streamlit as st
from datetime import date, timedelta
from lib.history_query import show_stock, show_date, show_compare
from lib.ui_helpers import build_stock_options, stock_name_map
from lib import watchlist_store
from components.history_chart import render_single_stock_timeline

st.title("📅 历史时序")

mode = st.radio("模式", ["单股", "单日", "同股diff"], horizontal=True)

# Build stock options once for modes that need it
watchlist_codes = watchlist_store.list_all()["code"].tolist() if not watchlist_store.list_all().empty else []
options = build_stock_options(watchlist_codes, stock_name_map(watchlist_codes))
labels = [l for l, _ in options]
values = [v for _, v in options]


def _pick_stock(label: str = "选股 (按名称排序)") -> str:
    return values[labels.index(st.selectbox(label, labels, key=label))]


if mode == "单股":
    if not watchlist_codes:
        st.info("自选股为空 — 先去 page 1 添加")
    else:
        code = _pick_stock()
        df = show_stock(code)
        render_single_stock_timeline(code, df)

elif mode == "单日":
    target = st.date_input("日期", date.today() - timedelta(days=1))
    df = show_date(target)
    if not df.empty:
        height = min(1500, max(300, len(df) * 28 + 60))
        st.dataframe(df, width="stretch", height=height, hide_index=True)
    else:
        st.info("该日期无数据")

elif mode == "同股diff":
    if not watchlist_codes:
        st.info("自选股为空 — 先去 page 1 添加")
    else:
        code = _pick_stock("选股 (按名称排序) - diff")
        result = show_compare(code)
        if result.get("first") is None:
            st.warning("历史不足 2 行")
        else:
            st.json(result["diff"])
