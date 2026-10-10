import pytest
from pathlib import Path
from lib.db import (
    get_conn, valuation_history_query, latest_for_codes,
    table_freshness, column_exists, CORE_TABLES, SCHEMA_VERSION,
)


# Skip all tests in this module if DuckDB not present
pytestmark = pytest.mark.skipif(
    not Path("E:/stock_db/stock_abase.duckdb").exists(),
    reason="Requires live DuckDB at E:/stock_db/stock_abase.duckdb",
)


def test_conn_is_read_only():
    conn = get_conn()
    with pytest.raises(Exception):  # read-only raises on any write
        conn.execute("CREATE TABLE _should_fail (x INT)")


def test_core_tables_has_11_entries():
    assert len(CORE_TABLES) == 11
    assert all(isinstance(t, tuple) and len(t) == 2 for t in CORE_TABLES)


def test_valuation_history_query_returns_dataframe():
    import pandas as pd
    df = valuation_history_query(code="000999", limit=5)
    assert isinstance(df, pd.DataFrame)
    assert "intrinsic_value" in df.columns


def test_column_exists_helper():
    assert column_exists("valuation_history", "intrinsic_value") is True
    assert column_exists("valuation_history", "nonexistent_col_xyz") is False


def test_table_freshness_returns_dataframe():
    import pandas as pd
    df = table_freshness()
    assert isinstance(df, pd.DataFrame)
    assert "table_name" in df.columns
