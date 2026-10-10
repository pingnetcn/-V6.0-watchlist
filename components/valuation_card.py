"""
13 books single-stock metric card (4 KPI tiles).
"""
import streamlit as st

METRIC_RENDERERS = {}


def register(name: str, fn):
    METRIC_RENDERERS[name] = fn


def _render_intrinsic(data):
    st.metric("评估价", f"¥{data.get('intrinsic_value', 0):.2f}")


def _render_margin(data):
    margin = data.get("margin", 0)
    st.metric("安全边际", f"{margin:+.1f}%", delta=f"{margin:+.1f}%",
              delta_color="normal" if margin > 0 else "inverse")


def _render_5y_range(data):
    bull = data.get("bull_price_5y", 0)
    bear = data.get("bear_price_5y", 0)
    st.metric("5年区间", f"¥{bear:.0f} – ¥{bull:.0f}")


def _render_fcff_quality(data):
    ratio = data.get("fcff_to_profit", 0)
    color = "normal" if 0.8 <= ratio <= 1.2 else "off"
    st.metric("FCFF/利润", f"{ratio:.2f}", delta_color=color)


register("intrinsic", _render_intrinsic)
register("margin", _render_margin)
register("5y_range", _render_5y_range)
register("fcff_quality", _render_fcff_quality)


def render(metric_name: str, data: dict):
    fn = METRIC_RENDERERS.get(metric_name)
    if fn:
        fn(data)
    else:
        st.warning(f"Unknown metric: {metric_name}")


def render_full(data: dict):
    cols = st.columns(4)
    with cols[0]:
        _render_intrinsic(data)
    with cols[1]:
        _render_margin(data)
    with cols[2]:
        _render_5y_range(data)
    with cols[3]:
        _render_fcff_quality(data)
