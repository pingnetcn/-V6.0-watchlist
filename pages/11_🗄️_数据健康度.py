"""Page 11: 数据健康度 — 仪表 + 运维入口."""
import subprocess
import streamlit as st
from lib.data_health import compute_full_health, MAINTENANCE_ACTIONS

st.title("🗄️ 数据健康度")

health = compute_full_health()
gh = health["global_health"]
cols = st.columns(4)
cols[0].metric("🟢 健康", gh["green"])
cols[1].metric("🟡 警告", gh["yellow"])
cols[2].metric("🔴 异常", gh["red"])
cols[3].metric("总表数", gh["green"] + gh["yellow"] + gh["red"])

st.subheader("§1 表新鲜度")
st.dataframe(health["table_freshness"], use_container_width=True)

st.subheader("§2 完整性矩阵 (Phase 3 完整版)")
st.info("自选股 × 数据源交叉表")

st.subheader("§3 兜底警告")
st.info("AI fallback / 限流状态 — Phase 3 完整版")

st.subheader("§4 维护操作")
acknowledged = st.checkbox("☐ 我明白会暂时影响 8905")

for key, action in MAINTENANCE_ACTIONS.items():
    if action.get("readonly"):
        if st.button(action["label"]):
            st.info("日志查看功能 — Phase 3 详细实现")
    else:
        disabled = not acknowledged
        if st.button(action["label"], disabled=disabled, key=f"btn_{key}"):
            if action.get("warning"):
                st.warning(action["warning"])
            try:
                proc = subprocess.Popen(action["command"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                st.success(f"已启动 (PID {proc.pid})")
            except Exception as e:
                st.error(f"启动失败: {e}")