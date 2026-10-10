"""
Cross-stock ranking + portfolio formation (wraps report_ranker).

How to extend:
    New filter on ranking? Wrap ReportRanker.rank() and filter result
    New format function? Add format_<name>(result) -> str

Public API:
    rank(cash_available=5_000_000, top_n=15, since_date=None, source='kb') -> dict
    format_markdown(result) -> str
"""
import sys
from pathlib import Path
from typing import Optional
from datetime import date

# Ensure main project is importable
from lib.paths import MAIN_PROJECT
if str(MAIN_PROJECT) not in sys.path:
    sys.path.insert(0, str(MAIN_PROJECT))

try:
    from scripts.report_ranker import ReportRanker
except ImportError:
    ReportRanker = None  # Will raise at call time with clear message

SCHEMA_VERSION = 1


def rank(
    cash_available: float = 5_000_000,
    top_n: int = 15,
    since_date: Optional[date] = None,
    source: str = "kb",
) -> dict:
    if ReportRanker is None:
        raise RuntimeError(
            f"ReportRanker not importable. Check MAIN_PROJECT path: {MAIN_PROJECT}"
        )
    ranker = ReportRanker()
    return ranker.rank(
        cash_available=cash_available,
        since_date=since_date,
        source=source,
    )


def format_markdown(result: dict) -> str:
    if ReportRanker is None:
        raise RuntimeError("ReportRanker not importable")
    ranker = ReportRanker()
    return ranker.format_markdown_report(result)
