"""
Read-only DuckDB access layer for valuation_history + table freshness.

Uses LOCAL REPLICA (E:/stock_db/.watchlist_data.duckdb) populated by
scripts/sync_watchlist_data.py — NOT main DB directly. This avoids the
file-lock conflict with main project (8905) which holds the source DuckDB
with exclusive write locks (see db_core.py monkey-patch + _kline.py
read_only=False long conns).

Sync schedule: manual via page 11 button, or cron every 5 min.

How to extend:
    Add new query function following naming: <noun>_<verb>(<filters>) -> DataFrame
    All queries MUST go through get_conn() — never open ad-hoc connections
    NEVER add write functions; this module is read-only by design

Public API:
    get_conn() -> duckdb.DuckDBPyConnection      (read_only=True, singleton)
    valuation_history_query(code, since, until, limit) -> DataFrame
    valuation_snapshot(target_date) -> DataFrame
    latest_for_codes(codes) -> DataFrame
    industry_benchmark(industry) -> DataFrame
    table_freshness() -> DataFrame
    coverage_stats(table, column) -> dict
    column_exists(table, column) -> bool
    get_sync_status() -> dict
"""
import duckdb
import pandas as pd
from typing import Optional
from datetime import date
from pathlib import Path
from lib.paths import DB_PATH

SCHEMA_VERSION = 2  # bumped: now reads from replica, not main

# Watchlist reads from LOCAL REPLICA, not main DB.
# The replica is populated by scripts/sync_watchlist_data.py.
REPLICA_PATH = Path(DB_PATH).parent / ".watchlist_data.duckdb"

CORE_TABLES = [
    ("valuation_history", "valuation_date"),
    ("stock_daily", "trade_date"),
    ("v_industry_benchmark", None),
]

_conn = None


def get_conn() -> duckdb.DuckDBPyConnection:
    """Get read-only DuckDB connection to LOCAL REPLICA.

    Raises clear error if replica doesn't exist (user needs to run sync).
    No lock conflict with main project because replica is a separate file.
    """
    global _conn
    if _conn is None:
        if not REPLICA_PATH.exists():
            raise RuntimeError(
                f"Watchlist replica not found: {REPLICA_PATH}\n"
                f"Run sync first: `python -m scripts.sync_watchlist_data`\n"
                f"Or click 'Sync now' button on page 11 (data health)."
            )
        _conn = duckdb.connect(str(REPLICA_PATH), read_only=True)
    return _conn


def get_sync_status() -> dict:
    """Get last sync timestamp + row counts. Returns dict with timestamps and per-table counts."""
    if not REPLICA_PATH.exists():
        return {"exists": False, "path": str(REPLICA_PATH)}
    try:
        conn = duckdb.connect(str(REPLICA_PATH), read_only=True)
        result = {"exists": True, "path": str(REPLICA_PATH), "tables": {}}
        # Get sync_log if it exists
        try:
            logs = conn.execute(
                "SELECT ts, table_name, rows_synced, duration_ms FROM sync_log ORDER BY id DESC LIMIT 10"
            ).df()
            result["recent_syncs"] = logs.to_dict("records")
        except Exception:
            result["recent_syncs"] = []
        # Row counts for CORE_TABLES
        for table, _ in CORE_TABLES:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                result["tables"][table] = count
            except Exception:
                result["tables"][table] = None
        conn.close()
        return result
    except Exception as e:
        return {"exists": True, "path": str(REPLICA_PATH), "error": str(e)}


def valuation_history_query(
    code: Optional[str] = None,
    since: Optional[date] = None,
    until: Optional[date] = None,
    limit: int = 1000,
) -> pd.DataFrame:
    conn = get_conn()
    sql = "SELECT * FROM valuation_history WHERE 1=1"
    params = []
    if code:
        sql += " AND code = ?"
        params.append(code)
    if since:
        sql += " AND valuation_date >= ?"
        params.append(since)
    if until:
        sql += " AND valuation_date <= ?"
        params.append(until)
    sql += f" ORDER BY valuation_date DESC LIMIT {limit}"
    return conn.execute(sql, params).df()


def valuation_snapshot(target_date: date) -> pd.DataFrame:
    return get_conn().execute(
        "SELECT * FROM valuation_history WHERE valuation_date = ?",
        [target_date],
    ).df()


def latest_for_codes(codes: list[str]) -> pd.DataFrame:
    if not codes:
        return pd.DataFrame()
    placeholders = ",".join(["?"] * len(codes))
    sql = f"""
        SELECT * FROM valuation_history
        WHERE code IN ({placeholders})
        QUALIFY ROW_NUMBER() OVER (PARTITION BY code ORDER BY valuation_date DESC) = 1
    """
    return get_conn().execute(sql, codes).df()


def industry_benchmark(industry: str) -> pd.DataFrame:
    """Query v_industry_benchmark by industry name.

    v_industry_benchmark columns are in Chinese (行业, 公司数, PE_TTM中位数, etc.)
    The main project's view is created by scripts/fix_v_industry_benchmark.py.
    """
    return get_conn().execute(
        'SELECT * FROM v_industry_benchmark WHERE "行业" = ?', [industry]
    ).df()


def table_freshness() -> pd.DataFrame:
    conn = get_conn()
    rows = []
    for table, date_col in CORE_TABLES:
        try:
            if date_col:
                max_date = conn.execute(
                    f"SELECT MAX({date_col}) FROM {table}"
                ).fetchone()[0]
            else:
                max_date = None
            rows.append({"table_name": table, "date_col": date_col, "max_date": max_date})
        except Exception:
            rows.append({"table_name": table, "date_col": date_col, "max_date": None})
    return pd.DataFrame(rows)


def coverage_stats(table: str, column: str) -> dict:
    conn = get_conn()
    row = conn.execute(
        f"SELECT COUNT(*) FILTER (WHERE {column} IS NOT NULL), COUNT(*) FROM {table}"
    ).fetchone()
    return {"filled": row[0], "total": row[1], "pct": row[0] / row[1] if row[1] else 0}


def column_exists(table: str, column: str) -> bool:
    try:
        cols = get_conn().execute(f"DESCRIBE {table}").fetchall()
        return any(c[0] == column for c in cols)
    except Exception:
        return False
