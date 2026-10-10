"""Page 11: 数据健康度 — 仪表 + 运维入口 + Sync 按钮."""
import subprocess
import streamlit as st
from lib.data_health import compute_full_health, MAINTENANCE_ACTIONS
from lib.db import get_sync_status, REPLICA_PATH

st.title("🗄️ 数据健康度")

# === Sync status (always visible at top) ===
sync_status = get_sync_status()
if sync_status.get("exists"):
    cols = st.columns(3)
    if sync_status.get("recent_syncs"):
        last = sync_status["recent_syncs"][0]
        cols[0].metric("Last sync", str(last.get("ts", "?"))[:19])
        cols[1].metric("Last rows", f"{last.get('rows_synced', 0):,}")
        cols[2].metric("Last duration", f"{last.get('duration_ms', 0)}ms")
    else:
        cols[0].info("No sync log yet")
    for tbl, cnt in sync_status.get("tables", {}).items():
        if cnt is not None:
            st.caption(f"  {tbl}: {cnt:,} rows")
else:
    st.error(f"⚠️ Replica 不存在: `{REPLICA_PATH}` — 请先跑 sync")

st.divider()

# === Health overview ===
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
st.info("AI fallback / 限流状态 — Phase 3 详细版")

st.subheader("§4 维护操作")

# Sync button (always enabled — no impact on 8905 since it uses replica)
if st.button("🔄 Sync now (从主 DuckDB 同步到本地 replica)"):
    with st.spinner("Sync 进行中… (如果主项目忙,会重试最多 2 分钟)"):
        try:
            result = subprocess.run(
                [".venv/Scripts/python.exe", "-m", "scripts.sync_watchlist_data"],
                capture_output=True, text=True, timeout=180,
            )
            st.code(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
            if result.returncode == 0:
                st.success("✓ Sync 完成! 刷新页面查看新数据")
            else:
                st.error(f"✗ Sync 失败 (exit {result.returncode})")
                st.code(result.stderr[-1500:])
        except subprocess.TimeoutExpired:
            st.error("✗ Sync 超时(>3 分钟)。主项目可能正在跑长时间 batch,稍后再试")
        except Exception as e:
            st.error(f"✗ Sync 出错: {e}")

st.divider()

# Other maintenance actions (require acknowledged checkbox)
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
