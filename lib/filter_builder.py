"""
Composable filter conditions for quick screener (page 9).
"""
from typing import Any, Callable
import pandas as pd

SCHEMA_VERSION = 1

TIER_ORDER = {"高": 3, "中": 2, "低": 1, "不可信": 0}


def _margin_gt(df, v): return df[df["margin"] > v]
def _margin_lt(df, v): return df[df["margin"] < v]
def _rating_in(df, v): return df[df["rating"].isin(v)]
def _rating_ge(df, v):
    order = ["F", "D", "C", "C+", "B", "B+", "A", "A+"]
    idx = order.index(v) if v in order else 0
    allowed = order[idx:]
    return df[df["rating"].isin(allowed)]
def _credibility_ge(df, v):
    threshold = TIER_ORDER.get(v, 0)
    return df[df["credibility"].map(lambda x: TIER_ORDER.get(x, 0)) >= threshold]
def _methods_spread_lt(df, v): return df[df["methods_spread"] < v]
def _failure_mode_count_lt(df, v):
    """Count comma-separated failure modes; filter rows with count < v.

    DuckDB stores failure_modes as comma-separated VARCHAR, e.g. "FM-01,FM-06".
    Count = number of commas + 1 if non-empty, 0 if empty/None.
    Examples:
        "FM-01,FM-06"      → 2 commas + 1 = 3
        "FM-01"            → 0 commas + 1 = 1
        "" (empty string)  → 0 commas + 0 = 0
        None               → 0 commas + 0 = 0 (after fillna(""))
    """
    comma_count = df["failure_modes"].fillna("").str.count(",")
    non_empty = df["failure_modes"].notna() & (df["failure_modes"] != "")
    return df[(comma_count + non_empty.astype(int)) < v]
def _company_type_in(df, v): return df[df["company_type"].isin(v)]
def _industry_in(df, v): return df[df["industry"].isin(v)]


FILTERS: dict[str, Callable[[pd.DataFrame, Any], pd.DataFrame]] = {
    "margin_gt": _margin_gt,
    "margin_lt": _margin_lt,
    "rating_in": _rating_in,
    "rating_ge": _rating_ge,
    "credibility_ge": _credibility_ge,
    "methods_spread_lt": _methods_spread_lt,
    "failure_mode_count_lt": _failure_mode_count_lt,
    "company_type_in": _company_type_in,
    "industry_in": _industry_in,
}


def apply(df: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    for name, value in filters.items():
        fn = FILTERS.get(name)
        if fn:
            df = fn(df, value)
    return df


def SUGGEST_RELAX(df: pd.DataFrame, current_filters: dict[str, Any]) -> str:
    """Try removing each filter one at a time; suggest the one that yields most results."""
    if not current_filters:
        return "无筛选条件"
    best_key = None
    best_count = -1
    for key in current_filters:
        relaxed = {k: v for k, v in current_filters.items() if k != key}
        result = apply(df, relaxed)
        if len(result) > best_count:
            best_count = len(result)
            best_key = key
    if best_key and best_count > 0:
        return f"💡 建议放宽: {best_key} (放宽后可得 {best_count} 只)"
    return "❌ 即使放宽所有条件仍无结果"