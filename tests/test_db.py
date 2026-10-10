"""Tests for lib/db.py — uses a local replica (E:/stock_db/.watchlist_data.duckdb).

The test fixture creates a fresh in-memory DuckDB with the same schema
as the replica, then patches REPLICA_PATH to point to it. This avoids any
need to read from main DB or have a real replica present.
"""
import pytest
from pathlib import Path
from unittest.mock import patch
import duckdb
import pandas as pd
from lib import db
from lib.db import (
    get_conn, valuation_history_query, latest_for_codes,
    table_freshness, column_exists, CORE_TABLES, SCHEMA_VERSION,
    REPLICA_PATH, get_sync_status,
)


@pytest.fixture
def replica_conn():
    """Create an in-memory DuckDB with the schema the watchlist expects."""
    conn = duckdb.connect(":memory:")
    # Minimal schema for tests
    conn.execute("""
        CREATE TABLE valuation_history (
            code VARCHAR,
            valuation_date DATE,
            intrinsic_value DOUBLE,
            margin DOUBLE,
            rating VARCHAR,
            credibility VARCHAR,
            bull_price_5y DOUBLE,
            bear_price_5y DOUBLE,
            fcff_intrinsic DOUBLE,
            pe_intrinsic DOUBLE,
            pb_intrinsic DOUBLE,
            iv_intrinsic DOUBLE,
            ev_intrinsic DOUBLE,
            failure_modes VARCHAR,
            methods_spread DOUBLE,
            current_price DOUBLE,
            name VARCHAR,
            industry VARCHAR,
            company_type VARCHAR
        )
    """)
    conn.execute("""
        INSERT INTO valuation_history VALUES
        ('000999', '2026-10-01', 34.34, 46.8, 'A', '高', 56.09, 17.68, 35.0, 30.0, 28.0, 32.0, 33.0, '', 79.4, 23.4, '华润三九', '医药', '稳定价值股'),
        ('000858', '2026-10-01', 150.0, 25.0, 'B+', '高', 200.0, 100.0, 145.0, 140.0, 130.0, 150.0, 148.0, 'FM-01', 60.0, 120.0, '五粮液', '白酒', '稳定价值股'),
        ('600519', '2026-10-01', 2000.0, 15.0, 'A+', '高', 3000.0, 1500.0, 1950.0, 1900.0, 1800.0, 2000.0, 1990.0, '', 50.0, 1739.0, '贵州茅台', '白酒', '稳定价值股')
    """)
    conn.execute("""
        CREATE TABLE stock_daily (
            code VARCHAR,
            trade_date DATE,
            open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE v_industry_benchmark (
            industry VARCHAR,
            median_pe DOUBLE,
            median_pb DOUBLE
        )
    """)
    yield conn
    conn.close()


@pytest.fixture
def patched_replica(replica_conn, monkeypatch, tmp_path):
    """Save replica to tmp file and patch REPLICA_PATH."""
    tmp_db = tmp_path / "test_replica.duckdb"
    # Copy in-memory db to tmp file
    disk_conn = duckdb.connect(str(tmp_db))
    disk_conn.execute(f"ATTACH ':memory:' AS mem_db")
    # Easier: re-execute all DDL+data on the disk db
    disk_conn.execute("""
        CREATE TABLE valuation_history (
            code VARCHAR, valuation_date DATE, intrinsic_value DOUBLE,
            margin DOUBLE, rating VARCHAR, credibility VARCHAR,
            bull_price_5y DOUBLE, bear_price_5y DOUBLE, fcff_intrinsic DOUBLE,
            pe_intrinsic DOUBLE, pb_intrinsic DOUBLE, iv_intrinsic DOUBLE,
            ev_intrinsic DOUBLE, failure_modes VARCHAR, methods_spread DOUBLE,
            current_price DOUBLE, name VARCHAR, industry VARCHAR, company_type VARCHAR
        )
    """)
    for row in replica_conn.execute("SELECT * FROM valuation_history").df().itertuples(index=False):
        disk_conn.execute(
            "INSERT INTO valuation_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            list(row),
        )
    disk_conn.execute("CREATE TABLE stock_daily (code VARCHAR, trade_date DATE, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume DOUBLE)")
    disk_conn.execute("CREATE TABLE v_industry_benchmark (industry VARCHAR, median_pe DOUBLE, median_pb DOUBLE)")
    disk_conn.close()

    monkeypatch.setattr(db, "REPLICA_PATH", tmp_db)
    # Reset singleton
    monkeypatch.setattr(db, "_conn", None)
    yield tmp_db


def test_replica_path_constant():
    """REPLICA_PATH should be alongside the main DB."""
    assert REPLICA_PATH.name == ".watchlist_data.duckdb"
    assert REPLICA_PATH.parent == Path("E:/stock_db")


def test_schema_version_2():
    """Schema version bumped: now reads from replica, not main."""
    assert SCHEMA_VERSION == 2


def test_core_tables_3_entries():
    """CORE_TABLES now has 3 entries (down from 11) — only watchlist-relevant ones."""
    assert len(CORE_TABLES) == 3
    table_names = [t[0] for t in CORE_TABLES]
    assert "valuation_history" in table_names
    assert "stock_daily" in table_names
    assert "v_industry_benchmark" in table_names


def test_conn_is_read_only(patched_replica):
    conn = get_conn()
    with pytest.raises(Exception):
        conn.execute("CREATE TABLE _should_fail (x INT)")


def test_valuation_history_query_returns_dataframe(patched_replica):
    df = valuation_history_query(code="000999", limit=5)
    assert isinstance(df, pd.DataFrame)
    assert "intrinsic_value" in df.columns
    assert len(df) == 1
    assert df.iloc[0]["rating"] == "A"


def test_latest_for_codes(patched_replica):
    df = latest_for_codes(["000999", "600519"])
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    codes = set(df["code"].tolist())
    assert codes == {"000999", "600519"}


def test_latest_for_codes_empty(patched_replica):
    df = latest_for_codes([])
    assert df.empty


def test_column_exists_helper(patched_replica):
    assert column_exists("valuation_history", "intrinsic_value") is True
    assert column_exists("valuation_history", "nonexistent_col_xyz") is False
    assert column_exists("nonexistent_table", "x") is False


def test_table_freshness_returns_dataframe(patched_replica):
    df = table_freshness()
    assert isinstance(df, pd.DataFrame)
    assert "table_name" in df.columns
    assert "valuation_history" in df["table_name"].tolist()


def test_get_sync_status(patched_replica):
    status = get_sync_status()
    assert status["exists"] is True
    assert "valuation_history" in status["tables"]
    assert status["tables"]["valuation_history"] == 3


def test_get_conn_missing_replica_raises(monkeypatch, tmp_path):
    """If replica doesn't exist, get_conn should raise clear error."""
    monkeypatch.setattr(db, "REPLICA_PATH", tmp_path / "nonexistent.duckdb")
    monkeypatch.setattr(db, "_conn", None)
    with pytest.raises(RuntimeError, match="Watchlist replica not found"):
        get_conn()
