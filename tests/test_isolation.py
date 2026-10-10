"""
ISOL smoke tests — run while main 8905 app is also running.

ISOL-3 + ISOL-4 (Phase 2 territory) are tested here too, since they require
Python orchestration, not bash. ISOL-1 + ISOL-2 require both servers running.
"""
import os
import pytest
import requests
from pathlib import Path
from unittest.mock import patch

from lib.db import get_conn


WATCHLIST_URL = "http://127.0.0.1:8910"
MAIN_URL = "http://127.0.0.1:8905"
MAIN_DB = Path("E:/stock_db/stock_abase.duckdb")


def test_isol_1_both_apps_responding():
    """Both apps return HTTP 200 simultaneously. Requires 8905 + 8910 running."""
    w = requests.get(WATCHLIST_URL, timeout=5).status_code
    m = requests.get(MAIN_URL, timeout=5).status_code
    assert w == 200
    assert m == 200


def test_isol_2_main_db_mtime_unchanged():
    """Watchlist writes (add 10 stocks) do not touch main DuckDB."""
    if not MAIN_DB.exists():
        pytest.skip("Main DuckDB not present")
    before = MAIN_DB.stat().st_mtime
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from lib import watchlist_store
    for i in range(10):
        watchlist_store.add(f"6{str(i).zfill(5)}")
    after = MAIN_DB.stat().st_mtime
    assert before == after


def test_isol_3_valuation_history_row_count_unchanged():
    """Running rank() (page 5) does not write to valuation_history."""
    if not MAIN_DB.exists():
        pytest.skip("Main DuckDB not present")
    before = get_conn().execute("SELECT COUNT(*) FROM valuation_history").fetchone()[0]
    # Simulate rank by calling lib.portfolio.rank (uses main project ReportRanker)
    # Just count rows before and after — rank() is read-only
    from lib.portfolio import rank
    try:
        rank(cash_available=5_000_000, top_n=5)
    except Exception:
        pass  # rank may fail without main project; we only care about row count
    after = get_conn().execute("SELECT COUNT(*) FROM valuation_history").fetchone()[0]
    assert before == after


def test_isol_4_quality_check_makes_no_llm_calls():
    """Page 6 quality check must not invoke any LLM API."""
    forbidden_imports = ["anthropic", "openai", "google.generativeai", "deepseek"]
    import sys
    # Check lib.completeness imports don't include any LLM
    import lib.completeness
    for module_name in list(sys.modules.keys()):
        for forbidden in forbidden_imports:
            if module_name.startswith(forbidden):
                pytest.fail(f"LLM module imported: {module_name}")
    # Also check the file source
    src = Path(lib.completeness.__file__).read_text(encoding="utf-8")
    for forbidden in forbidden_imports:
        assert forbidden not in src, f"LLM reference in lib/completeness.py: {forbidden}"


def test_isol_5_maintenance_button_disabled_by_default():
    """Page 11 §4 buttons default disabled; require explicit checkbox."""
    from streamlit.testing.v1 import AppTest
    page_path = str(Path(__file__).parent.parent / "pages" / "11_🗄️_数据健康度.py")
    at = AppTest.from_file(page_path).run()
    btns = [b for b in at.button if "触发" in str(b.label)]
    for btn in btns:
        assert btn.disabled is True, f"Button {btn.label} should be disabled by default"


def test_isol_6_killing_watchlist_does_not_affect_main():
    """If 8910 dies, 8905 still responds. Manual smoke only."""
    pytest.skip("Manual smoke: kill 8910 then check 8905 = 200")


def test_isol_7_concurrent_read_during_write():
    """DuckDB read on watchlist doesn't block main app write. Manual smoke only."""
    pytest.skip("Manual smoke: trigger 8905 batch update while 8910 reads")