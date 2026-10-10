"""Page 11: 数据健康度 — 详细诊断 + 可执行修正建议."""
import subprocess
from datetime import datetime, date, timedelta
import pandas as pd
import streamlit as st
from lib import watchlist_store
from lib.data_health import compute_full_health, MAINTENANCE_ACTIONS
from lib.db import get_sync_status, REPLICA_PATH, get_conn, valuation_history_query

st.title("🗄️ 数据健康度")

# ============================================================
# Section A: Sync status (top, always visible)
# ============================================================
st.subheader("📡 A. 同步状态")
sync_status = get_sync_status()
if sync_status.get("exists"):
    cols = st.columns(4)
    if sync_status.get("recent_syncs"):
        last = sync_status["recent_syncs"][0]
        # ts might be a string or datetime
        ts_raw = last.get("ts", "?")
        ts_str = str(ts_raw)[:19] if ts_raw else "?"
        cols[0].metric("Last sync", ts_str)
        cols[1].metric("Last rows", f"{last.get('rows_synced', 0):,}")
        cols[2].metric("Last duration", f"{last.get('duration_ms', 0)}ms")
        # Age
        try:
            ts_dt = pd.Timestamp(ts_raw)
            age_min = (pd.Timestamp.now() - ts_dt).total_seconds() / 60
            cols[3].metric("Age", f"{age_min:.0f} min")
        except Exception:
            cols[3].metric("Age", "?")

    # Per-table row counts
    st.caption("Replica row counts:")
    table_cols = st.columns(len(sync_status.get("tables", {})) or 1)
    for i, (tbl, cnt) in enumerate(sync_status.get("tables", {}).items()):
        if i < len(table_cols):
            table_cols[i].metric(tbl, f"{cnt:,}" if cnt is not None else "—")
else:
    st.error(f"⚠️ Replica 不存在: `{REPLICA_PATH}` — 请先跑 sync")

st.divider()

# ============================================================
# Section B: Replica table freshness (when each table was last updated)
# ============================================================
st.subheader("📅 B. 表新鲜度 (每张表最新数据时间)")
health = compute_full_health()
freshness_df = health["table_freshness"]

# Enhance with age column
def _age_str(max_date):
    if max_date is None or pd.isna(max_date):
        return "—"
    try:
        md = pd.Timestamp(max_date)
        days = (date.today() - md.date()).days
        if days == 0:
            return "今天"
        if days == 1:
            return "1 天前"
        return f"{days} 天前"
    except Exception:
        return "?"

if not freshness_df.empty:
    freshness_df = freshness_df.copy()
    freshness_df["age"] = freshness_df["max_date"].apply(_age_str)
    # Sort by age (most stale first)
    freshness_display = freshness_df[["table_name", "age", "max_date", "date_col"]].rename(
        columns={"table_name": "表名", "age": "距今", "max_date": "最新数据日期", "date_col": "日期列"}
    )
    height = min(800, max(200, len(freshness_display) * 32 + 60))
    st.dataframe(freshness_display, width="stretch", height=height, hide_index=True)

    # Flag stale tables (only tables WITH date_col can be "stale")
    stale = []
    for _, row in freshness_df.iterrows():
        date_col = row.get("date_col")
        # Skip reference tables (no date col) — they're not "stale", just don't track time
        if date_col is None or (isinstance(date_col, float) and pd.isna(date_col)):
            continue
        md = row.get("max_date")
        if md is None or pd.isna(md):
            stale.append((row["table_name"], "无数据"))
            continue
        try:
            days = (date.today() - pd.Timestamp(md).date()).days
            if days > 7:
                stale.append((row["table_name"], f"{days} 天前"))
        except Exception:
            pass
    if stale:
        st.warning(f"⚠️ {len(stale)} 张表数据陈旧 (>7 天): " + ", ".join(f"{t} ({a})" for t, a in stale))
    else:
        st.success("✅ 所有有时间的表数据都在 7 天内")
else:
    st.info("无新鲜度数据 (replica 为空?)")

st.divider()

# ============================================================
# Section C: Watchlist coverage (do all watchlist stocks have valuation?)
# ============================================================
st.subheader("📋 C. 自选股覆盖度")
watchlist = watchlist_store.list_all()
if watchlist.empty:
    st.info("自选股为空")
else:
    codes = watchlist["code"].tolist()
    try:
        snapshot = valuation_history_query(limit=10000)
        have_data = set(snapshot["code"].unique()) if not snapshot.empty else set()
        missing = [c for c in codes if c not in have_data]
        coverage_pct = (len(codes) - len(missing)) / len(codes) * 100 if codes else 0

        cols = st.columns(3)
        cols[0].metric("自选股总数", len(codes))
        cols[1].metric("有估值报告", f"{len(codes) - len(missing)} ({coverage_pct:.0f}%)")
        cols[2].metric("缺估值报告", len(missing), delta=-len(missing) if missing else 0, delta_color="inverse")

        if missing:
            with st.expander(f"⚠️ 缺失股票 ({len(missing)} 只)", expanded=False):
                st.code(", ".join(missing[:50]) + ("..." if len(missing) > 50 else ""))
                st.caption("💡 修正: 跑 sync 把主项目最新估值同步过来。如果没有,说明主项目还没为这些股票生成报告。")
    except Exception as e:
        st.error(f"覆盖度查询失败: {e}")

st.divider()

# ============================================================
# Section D: 估值质量分布 (credibility, rating, failure modes)
# ============================================================
st.subheader("🎯 D. 估值质量分布")
try:
    if not snapshot.empty:
        cols = st.columns(2)
        with cols[0]:
            st.caption("**评级分布** (自选股最新估值)")
            rating_dist = snapshot["rating"].value_counts().reset_index()
            rating_dist.columns = ["评级", "数量"]
            st.dataframe(rating_dist, width="stretch", height=250, hide_index=True)
        with cols[1]:
            st.caption("**可信度分布**")
            cred_dist = snapshot["credibility"].value_counts().reset_index()
            cred_dist.columns = ["可信度", "数量"]
            st.dataframe(cred_dist, width="stretch", height=250, hide_index=True)

        # Top failure modes
        st.caption("**Top 失败模式** (跨自选股累计触发)")
        all_fms = []
        for fms in snapshot["failure_modes"].fillna(""):
            if fms:
                all_fms.extend([f.strip() for f in str(fms).split(",") if f.strip()])
        if all_fms:
            fm_dist = pd.Series(all_fms).value_counts().head(10).reset_index()
            fm_dist.columns = ["失败模式", "触发次数"]
            st.dataframe(fm_dist, width="stretch", height=300, hide_index=True)
        else:
            st.success("✅ 自选股中没有失败模式触发")

        # Method spread warning
        high_spread = snapshot[snapshot["methods_spread"].fillna(0) > 100]
        if not high_spread.empty:
            st.warning(
                f"⚠️ {len(high_spread)} 只股票方法分歧 > 100% (估值不确定性高)"
            )
    else:
        st.info("无估值数据")
except Exception as e:
    st.error(f"质量分析失败: {e}")

st.divider()

# ============================================================
# Section E: 修正建议 (actionable)
# ============================================================
st.subheader("🔧 E. 修正建议")
issues = []
fixes = []

# 1. Sync status
if not sync_status.get("exists"):
    issues.append("🔴 Replica 不存在,watchlist 无法读数据")
    fixes.append("→ 跑 `python -m scripts.sync_data` 或点下面 'Sync now'")
elif sync_status.get("recent_syncs"):
    last = sync_status["recent_syncs"][0]
    try:
        ts_dt = pd.Timestamp(last.get("ts"))
        age_min = (pd.Timestamp.now() - ts_dt).total_seconds() / 60
        if age_min > 60:
            issues.append(f"🟡 同步数据已 {age_min:.0f} 分钟未更新")
            fixes.append("→ 点 'Sync now' 或设置 cron 每 30-60 分钟跑一次")
    except Exception:
        pass

# 2. Stale tables
if not freshness_df.empty:
    for _, row in freshness_df.iterrows():
        md = row.get("max_date")
        if md is None or pd.isna(md):
            issues.append(f"🟡 表 {row['table_name']} 无数据 (replica 还没建或 sync 失败)")
            fixes.append(f"→ 跑 sync;如果还是空,主项目里 {row['table_name']} 也是空的")
            break
        try:
            days = (date.today() - pd.Timestamp(md).date()).days
            if days > 7:
                issues.append(f"🟡 表 {row['table_name']} 数据 {days} 天前")
        except Exception:
            pass
    if any("数据" in i and "天前" in i for i in issues) and not any(f.startswith("→ 设置 cron") for f in fixes):
        fixes.append("→ 设置 cron 定期跑 sync;主项目 daily_update 也会刷新数据")

# 3. Missing watchlist coverage
if not watchlist.empty:
    try:
        snap = valuation_history_query(limit=10000)
        have = set(snap["code"].unique()) if not snap.empty else set()
        miss = [c for c in watchlist["code"].tolist() if c not in have]
        if miss:
            issues.append(f"🟡 {len(miss)} 只自选股无估值报告")
            fixes.append("→ 这些股票主项目还没生成报告,等 nightly batch 或手动触发 daily_update")
    except Exception:
        pass

# 4. Method spread
if not snapshot.empty and "methods_spread" in snapshot.columns:
    high = snapshot[snapshot["methods_spread"].fillna(0) > 100]
    if not high.empty:
        issues.append(f"🟡 {len(high)} 只股票方法分歧 > 100%")
        fixes.append("→ 这些是估值不确定的股票,谨慎看;可去 page 6 质量校验看详情")

# Display
if not issues:
    st.success("✅ 没有发现数据问题。Replica 状态健康。")
else:
    st.markdown("**🔍 发现的问题:**")
    for issue in issues:
        st.markdown(f"- {issue}")
    st.markdown("")
    st.markdown("**💡 修正建议:**")
    for fix in fixes:
        st.markdown(f"- {fix}")

st.divider()

# ============================================================
# Section F: Sync button + maintenance actions
# ============================================================
st.subheader("🔄 F. 维护操作")

# Sync button
if st.button("🔄 Sync now (从主 DuckDB 同步到本地 replica)"):
    with st.spinner("Sync 进行中… (主项目忙时最多重试 2 分钟)"):
        try:
            # v6.97+ fix: Windows Popen + 相对路径 抛 [WinError 2] — 必须用绝对路径
            import os as _os
            _project_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
            _vpy = _os.path.join(_project_root, ".venv", "Scripts", "python.exe")
            result = subprocess.run(
                [_vpy, "-m", "scripts.sync_watchlist_data"],
                capture_output=True, text=True, timeout=180,
                cwd=_project_root,
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

# Other maintenance actions (checkbox defaults to checked per user request)
acknowledged = st.checkbox(
    "☐ 我明白会暂时影响 8905",
    value=True,
    help="默认勾选。取消勾选会禁用下面的写操作按钮。",
)
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
