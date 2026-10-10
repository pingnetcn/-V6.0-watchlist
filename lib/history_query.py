"""
Historical valuation queries (extracted from scripts/_query_valuation_history.py).

How to extend:
    Add new query function for backtest/visualization needs
    Use conn parameter (not hardcoded) for testability

Public API:
    show_stock(code, conn=None) -> DataFrame
    show_date(target_date, conn=None) -> DataFrame
    show_compare(code, conn=None) -> dict
    compute_valuation_accuracy(code, horizons_days=[30,90,180,365], conn=None) -> DataFrame
"""
from typing import Optional
from datetime import date
import pandas as pd
from lib.db import get_conn, valuation_history_query

SCHEMA_VERSION = 1


def show_stock(code: str, conn=None) -> pd.DataFrame:
    conn = conn or get_conn()
    return conn.execute(
        "SELECT * FROM valuation_history WHERE code = ? ORDER BY valuation_date DESC",
        [code],
    ).df()


def show_date(target_date: date, conn=None) -> pd.DataFrame:
    conn = conn or get_conn()
    return conn.execute(
        "SELECT * FROM valuation_history WHERE valuation_date = ?",
        [target_date],
    ).df()


def show_compare(code: str, conn=None) -> dict:
    df = show_stock(code, conn=conn)
    if len(df) < 2:
        return {"first": None, "last": None, "diff": None}
    first, last = df.iloc[-1], df.iloc[0]
    return {
        "first": first.to_dict(),
        "last": last.to_dict(),
        "diff": {
            "iv_delta_pct": (last["intrinsic_value"] - first["intrinsic_value"]) / first["intrinsic_value"] * 100,
            "price_delta_pct": (last["current_price"] - first["current_price"]) / first["current_price"] * 100,
            "margin_delta_pp": last["margin"] - first["margin"],
            "rating_change": f"{first['rating']} → {last['rating']}",
        },
    }


def compute_valuation_accuracy(
    code: str,
    horizons_days: list[int] = [30, 90, 180, 365],
    conn=None,
) -> pd.DataFrame:
    """Predict date vs actual price at T+N horizons."""
    from datetime import timedelta
    conn = conn or get_conn()
    history = show_stock(code, conn=conn)
    rows = []
    for _, row in history.iterrows():
        predict_date = row["valuation_date"]
        predicted_iv = row["intrinsic_value"]
        for n in horizons_days:
            target_date = predict_date + timedelta(days=n)
            try:
                # A 股 stock_daily; 港股 hk_stock_daily
                actual_df = conn.execute(
                    "SELECT close FROM stock_daily WHERE code = ? AND trade_date <= ? ORDER BY trade_date DESC LIMIT 1",
                    [code, target_date],
                ).df()
                if actual_df.empty:
                    continue
                actual_price = actual_df["close"].iloc[0]
                abs_error = abs(actual_price - predicted_iv) / predicted_iv * 100
                rows.append({
                    "predict_date": predict_date,
                    "predicted_iv": predicted_iv,
                    "horizon_days": n,
                    "actual_price": actual_price,
                    "abs_error_pct": abs_error,
                    "sign_correct": (actual_price > row["current_price"]) == (predicted_iv > row["current_price"]),
                })
            except Exception:
                continue
    return pd.DataFrame(rows)