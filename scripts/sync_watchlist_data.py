"""Sync main DuckDB → watchlist local DuckDB replica.

Why: main project's DuckDB file is held with exclusive locks (write conns in
_kline.py, monkey-patched duckdb.connect in db_core.py) that block watchlist
from concurrent read_only opens. Solution: copy a subset to a local replica
that watchlist reads from, fully decoupled from main.

Usage:
    # Initial sync (may take 30s-2min if main is busy)
    python -m scripts.sync_watchlist_data

    # Tables to sync (default: valuation_history, stock_daily, v_industry_benchmark)
    python -m scripts.sync_watchlist_data --tables valuation_history,stock_daily

How it works:
    1. Open main DuckDB with retry (waits for main to release lock)
    2. SELECT all rows from each table
    3. Open local replica (separate file, no lock conflict)
    4. DROP + CREATE in replica
    5. Log to sync_log table

Schedule via:
    - Manual: page 11 "Sync now" button
    - Cron: every 5 min during market hours
    - Initial: run once before first watchlist use
"""
import sys
import io
import time
import argparse
from pathlib import Path
from datetime import datetime
import duckdb

# Force UTF-8 stdout (Windows GBK can't encode some chars in print)
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("gbk"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Allow this script to import from lib/
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.paths import DB_PATH  # noqa: E402

MAIN_DB = Path(DB_PATH)
REPLICA_DB = MAIN_DB.parent / ".watchlist_data.duckdb"

# Tables to mirror. (table_name, has_date_col)
# - valuation_history: critical, used by pages 1, 3, 4, 6, 10
# - stock_daily: needed for page 10 估值回测 (actual price at T+N)
# - v_industry_benchmark: page 8 行业板块
DEFAULT_TABLES = [
    ("valuation_history", True),
    ("stock_daily", True),
    ("v_industry_benchmark", False),
]


def open_main_with_retry(max_attempts: int = 60, sleep: float = 2.0):
    """Try to open main DuckDB read-only with retry.

    Waits up to max_attempts * sleep seconds (default 2 min). If main is
    doing a long batch (>2 min), this will fail — run during off-hours.
    """
    for attempt in range(max_attempts):
        try:
            return duckdb.connect(str(MAIN_DB), read_only=True)
        except duckdb.IOException as e:
            msg = str(e).lower()
            if ("already open" in msg or "locked" in msg or "being used" in msg) and attempt < max_attempts - 1:
                if attempt == 0 or attempt % 10 == 0:
                    print(f"  Main DB locked, retry {attempt+1}/{max_attempts}...")
                time.sleep(sleep)
                continue
            raise
    raise RuntimeError(f"Could not open main DB after {max_attempts} retries (~{max_attempts * sleep}s)")


def _replica_locked_check() -> str | None:
    """检测 replica DB 是否被其他进程持有 (watchlist Streamlit 8910 读锁).

    Returns: 错误信息字符串 (锁定时) / None (可写).
    v6.97.10+: 在 sync 写入 replica 前检测, 给出可操作的提示 (停 watchlist → 跑 sync → 重启).

    设计: 用 read_only=False 探测 (试拿写锁) — DuckDB 多 read_only 可并存, 但写锁互斥.
    """
    try:
        probe = duckdb.connect(str(REPLICA_DB), read_only=False)
        probe.close()
    except duckdb.IOException as e:
        msg = str(e)
        if "另一个程序正在使用" in msg or "being used" in msg or "locked" in msg:
            return (
                f"Replica DB 被 watchlist Streamlit (8910) 持有读锁.\n"
                f"  DuckDB 不允许 write 同时另一进程 read-only.\n"
                f"  修法 3 步:\n"
                f"    1. taskkill //F //PID <watchlist_pid>    (停 watchlist)\n"
                f"    2. .venv/Scripts/python.exe -m scripts.sync_watchlist_data\n"
                f"    3. restart.bat           (重启)\n"
                f"  原错误: {msg[:120]}"
            )
    return None


def sync(tables: list) -> dict:
    """Sync specified tables from main to replica. Returns sync stats."""
    print(f"[{datetime.now().isoformat(timespec='seconds')}] Starting sync")
    print(f"  Main:   {MAIN_DB}")
    print(f"  Replica: {REPLICA_DB}")
    print(f"  Tables: {[t[0] for t in tables]}")

    src = open_main_with_retry()
    print("  [OK] Main DB opened (read-only)")

    # v6.97.10+: 在打开 replica 前检测是否被 watchlist Streamlit 持有, 避免中途失败
    locked_msg = _replica_locked_check()
    if locked_msg:
        raise RuntimeError(locked_msg)

    REPLICA_DB.parent.mkdir(parents=True, exist_ok=True)
    dst = duckdb.connect(str(REPLICA_DB), read_only=False)
    print("  [OK] Replica DB opened (read-write)")

    # Create sync_log table (DuckDB 1.5.6 doesn't support IDENTITY; use ts as natural sort key)
    dst.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            table_name VARCHAR,
            rows_synced INTEGER,
            duration_ms INTEGER
        )
    """)

    stats = {"tables": {}, "total_rows": 0, "total_ms": 0}
    overall_start = time.time()

    for table, _ in tables:
        start = time.time()
        try:
            # Check table exists in main
            exists = src.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = ?",
                [table],
            ).fetchone()
            if not exists:
                print(f"  [skip] {table}: not found in main, skipping")
                continue

            # Copy
            df = src.execute(f"SELECT * FROM {table}").df()
            dst.execute(f"DROP TABLE IF EXISTS {table}")
            # Use CREATE TABLE AS for proper types
            dst.execute(f"CREATE TABLE {table} AS SELECT * FROM df")

            count = len(df)
            elapsed = int((time.time() - start) * 1000)
            stats["tables"][table] = {"rows": count, "ms": elapsed}
            stats["total_rows"] += count
            print(f"  [OK] {table}: {count:,} rows in {elapsed}ms")
        except Exception as e:
            print(f"  [FAIL] {table}: FAILED - {e}")
            stats["tables"][table] = {"error": str(e)}

    stats["total_ms"] = int((time.time() - overall_start) * 1000)

    # Log
    dst.execute(
        "INSERT INTO sync_log (table_name, rows_synced, duration_ms) VALUES (?, ?, ?)",
        ["__ALL__", stats["total_rows"], stats["total_ms"]],
    )

    src.close()
    dst.close()

    print(f"\n[OK] Sync complete in {stats['total_ms']}ms")
    print(f"  Total rows synced: {stats['total_rows']:,}")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Sync main DuckDB -> watchlist replica")
    parser.add_argument(
        "--tables",
        type=str,
        default=",".join(t[0] for t in DEFAULT_TABLES),
        help="Comma-separated table names to sync",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=60,
        help="Max retries waiting for main DB lock (default 60, ~2 min)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=2.0,
        help="Seconds between retries (default 2.0)",
    )
    args = parser.parse_args()

    table_names = set(args.tables.split(","))
    tables = [t for t in DEFAULT_TABLES if t[0] in table_names]

    try:
        sync(tables)
    except Exception as e:
        print(f"\n[FAIL] Sync FAILED: {e}")
        # v6.97.10+: 副本被 8910 watchlist 持有是常见冲突, 提示用户操作步骤
        if "Replica DB" in str(e) or "8910" in str(e):
            print("\n→ watchlist Streamlit (8910) 必须先停, 才能跑 sync.")
        else:
            print("\nTo sync, you may need to briefly stop the watchlist project (8910):")
            print("  1. Stop watchlist streamlit (port 8910)")
            print("  2. Run this script: python -m scripts.sync_watchlist_data")
            print("  3. Restart watchlist streamlit")
        sys.exit(1)


if __name__ == "__main__":
    main()
