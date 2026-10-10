import pandas as pd
import pytest
from pathlib import Path
from lib.history_query import (
    show_stock, show_date, show_compare, compute_valuation_accuracy,
    SCHEMA_VERSION,
)


# Skip all tests in this module if DuckDB not present (M3 patch)
pytestmark = pytest.mark.skipif(
    not Path("E:/stock_db/stock_abase.duckdb").exists(),
    reason="Requires live DuckDB at E:/stock_db/stock_abase.duckdb",
)


def test_schema_version():
    assert SCHEMA_VERSION == 1


def test_show_stock_returns_dataframe():
    df = show_stock("000999")
    assert isinstance(df, pd.DataFrame)
    assert "valuation_date" in df.columns


def test_show_compare_returns_dict():
    result = show_compare("000999")
    assert "first" in result
    assert "last" in result
    assert "diff" in result


def test_compute_valuation_accuracy_returns_dataframe():
    df = compute_valuation_accuracy("000999", horizons_days=[30, 90])
    assert isinstance(df, pd.DataFrame)
    assert "horizon_days" in df.columns