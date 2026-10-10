"""Page 2: 单股深读 — 全文报告 + KPI 卡片."""
import streamlit as st
from lib import watchlist_store
from lib.db import latest_for_codes
from lib.valuation_reader import latest_version, parse_full_report
from components.valuation_card import render_full

st.title("📈 单股深读")

df = watchlist_store.list_all()
if df.empty:
    st.warning("自选股为空 — 先去 page 1 添加")
    st.stop()

# Build a {code: name} map from replica (latest_for_codes returns name + code)
codes = df["code"].tolist()
try:
    snapshot = latest_for_codes(codes)
    name_map = dict(zip(snapshot["code"], snapshot["name"]))
except Exception:
    # Fallback: empty names
    name_map = {c: "" for c in codes}

# Build display labels: "贵州茅台 (600519)" or just "600519" if no name
options = []
for c in codes:
    name = name_map.get(c) or ""
    if name and not pd_isna(name):
        options.append((f"{name} ({c})", c))
    else:
        options.append((c, c))

# Sort by name for easier browsing
options.sort(key=lambda x: x[0])

labels = [label for label, _ in options]
values = [value for _, value in options]

# Find default (first item)
default_idx = 0
selected_label = st.selectbox("选股 (按名称排序)", labels, index=default_idx)
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


def pd_isna(x):
    try:
        import math
        if x is None:
            return True
        if isinstance(x, float) and math.isnan(x):
            return True
        return False
    except Exception:
        return False
