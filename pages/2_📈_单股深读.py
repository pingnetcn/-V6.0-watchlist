"""Page 2: 单股深读 — 全文报告 + KPI 卡片."""
import streamlit as st
from lib import watchlist_store
from lib.valuation_reader import latest_version, parse_full_report
from lib.ui_helpers import build_stock_options, stock_name_map
from components.valuation_card import render_full

st.title("📈 单股深读")

df = watchlist_store.list_all()
if df.empty:
    st.warning("自选股为空 — 先去 page 1 添加")
    st.stop()

codes = df["code"].tolist()
options = build_stock_options(codes, stock_name_map(codes))
labels = [label for label, _ in options]
values = [value for _, value in options]

selected_label = st.selectbox("选股 (按名称排序)", labels, index=0)
code = values[labels.index(selected_label)]

version_path = latest_version(code)

if version_path is None:
    st.error(f"未找到 {code} 的估值报告")
    st.stop()

report = parse_full_report(version_path)
st.caption(f"Version: {report['metadata'].get('version', '?')}")

render_full(report["metadata"])

for num, body in sorted(report["sections"].items()):
    with st.expander(f"§{num}"):
        st.markdown(body)
