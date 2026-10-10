"""
Read-only DuckDB access layer for valuation_history + table freshness.

How to extend:
    Add new query function following naming: <noun>_<verb>(<filters>) -> DataFrame
    All queries MUST go through get_conn() — never open ad-hoc connections
    NEVER add write functions; this module is read-only by design

Public API:
    get_conn() -> duckdb.DuckDBPyConnection      (read_only=True, singleton with retry)
    valuation_history_query(code, since, until, limit) -> DataFrame
    valuation_snapshot(target_date) -> DataFrame
    latest_for_codes(codes) -> DataFrame
    industry_benchmark(industry) -> DataFrame
    table_freshness() -> DataFrame
    coverage_stats(table, column) -> dict
    column_exists(table, column) -> bool
"""
import time
import duckdb
import pandas as pd
from typing import Optional
from datetime import date
from lib.paths import DB_PATH

SCHEMA_VERSION = 1

CORE_TABLES = [
    ("stock_daily", "trade_date"),
    ("stock_basic", None),
    ("stock_technical", "trade_date"),
    ("v_financial_metrics", "report_date"),
    ("v_share_structure", "report_date"),
    ("valuation_history", "valuation_date"),
    ("hk_stock_basic", None),
    ("hk_stock_daily", "trade_date"),
    ("hk_stock_technical", "trade_date"),
    ("hk_daily_valuation", "trade_date"),
    ("hk_valuation_cache", "ts"),
]

_conn = None


def _is_alive(conn) -> bool:
    try:
        conn.execute("SELECT 1").df()
        return True
    except Exception:
        return False


def get_conn() -> duckdb.DuckDBPyConnection:
    """Get read-only DuckDB connection with retry on file-lock conflicts.

    Main project (port 8905) often holds the DuckDB file briefly during writes.
    DuckDB 1.5.6 on Windows can refuse concurrent opens even for read_only.
    We retry up to 8 times (totaling ~6s of backoff) before giving up.
    """
    global _conn
    if _conn is not None and _is_alive(_conn):
        return _conn
    if _conn is not None:
        try:
            _conn.close()
        except Exception:
            pass
        _conn = None

    last_err = None
    for attempt in range(8):
        try:
            _conn = duckdb.connect(str(DB_PATH), read_only=True)
            return _conn
        except duckdb.IOException as e:
            last_err = e
            msg = str(e).lower()
            if "already open" in msg or "locked" in msg or "being used" in msg:
                time.sleep(0.2 * (attempt + 1))  # 0.2, 0.4, ..., 1.6
                continue
            raise

    raise RuntimeError(
        f"DuckDB file is held by another process (likely main 8905 doing a write). "
        f"After 8 retries (~6s), could not open {DB_PATH}. "
        f"Either wait for main to finish, or briefly stop the main app. "
        f"Underlying error: {last_err}"
    )


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
    return get_conn().execute(
        "SELECT * FROM v_industry_benchmark WHERE industry = ?", [industry]
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
