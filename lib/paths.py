"""
Bootstrap sys.path to access main project modules, expose path constants.

How to extend:
    If main project moves, edit MAIN_PROJECT default below.
    New paths? Add constants, never hardcode drive letters elsewhere.

Public API:
    MAIN_PROJECT: Path
    DB_PATH: Path
    VAL_REPORTS_DIR: Path
    get_main_project() -> Path

Depends on: tradingagents.dataflows.paths (via sys.path)
"""
import os
import sys
from pathlib import Path

SCHEMA_VERSION = 1

DEFAULT_MAIN_PROJECT = Path(__file__).parent.parent.parent / "陈氏鉴股V6.0-v697"

MAIN_PROJECT = Path(os.environ.get("WATCHLIST_MAIN_PROJECT", str(DEFAULT_MAIN_PROJECT)))

if str(MAIN_PROJECT) not in sys.path and MAIN_PROJECT.exists():
    sys.path.insert(0, str(MAIN_PROJECT))

try:
    from tradingagents.dataflows.paths import DB_PATH as _DB_PATH, HK_DB_PATH
    DB_PATH = Path(os.environ.get("WATCHLIST_DB_PATH", str(_DB_PATH)))
except ImportError:
    DB_PATH = Path(os.environ.get(
        "WATCHLIST_DB_PATH", "E:/stock_db/stock_abase.duckdb"
    ))

VAL_REPORTS_DIR = Path(os.environ.get("WATCHLIST_VAL_DIR", "E:/stock/Val"))


def get_main_project() -> Path:
    return MAIN_PROJECT