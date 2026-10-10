"""Cross-stock ranking + portfolio formation — local version (no main project deps).

The original lib/portfolio.rank() wraps main project's ReportRanker, which
triggers an import chain requiring yfinance/langchain_core/etc. that the
watchlist venv doesn't have. This local version queries the replica directly
and applies the same BUY criteria:

BUY requires: composite_score >= 60 AND data_credibility >= 0.30 AND margin > 0
SELL: rating in (D, F) OR margin < -20%
HOLD: everything else

Returns same dict shape as report_ranker for drop-in compatibility:
    {
        buy_list: [{code, name, score, weight, current_price, intrinsic_value, ...}, ...],
        sell_list: [...],
        hold_list: [...],
        portfolio_metrics: {buy_count, ...},
        sector_allocation: {industry: weight, ...},
        risk_warnings: [...],
    }
"""
import sys
import pandas as pd
from typing import Optional
from datetime import datetime
from lib.db import latest_for_codes, get_conn

# Re-export original rank() if user wants main project version
from lib.portfolio import SCHEMA_VERSION as _SCHEMA  # noqa


# Credit-to-numeric mapping
CREDIBILITY_SCORE = {"高": 1.0, "中": 0.6, "低": 0.3, "不可信": 0.0}

# Rating numeric
RATING_SCORE = {
    "A+": 100, "A": 90, "B+": 80, "B": 70,
    "C+": 60, "C": 50, "D": 30, "F": 10,
}


def _composite_score(credibility: str, rating: str, margin: float) -> float:
    """Composite score 0-100. Weighted: credibility 40%, rating 40%, margin 20%."""
    cred = CREDIBILITY_SCORE.get(credibility, 0.0)
    rate = RATING_SCORE.get(rating, 30)
    # Margin: 0% = 50, +50% = 100, -50% = 0
    margin_score = max(0, min(100, 50 + margin))
    return cred * 40 + (rate / 100) * 40 + margin_score * 0.2


def rank_local(
    cash_available: float = 5_000_000,
    top_n: int = 15,
    codes: Optional[list[str]] = None,
    min_credibility: str = "中",
    min_margin: float = 0.0,
) -> dict:
    """Rank stocks for portfolio using replica data only.

    Args:
        cash_available: total capital to allocate (¥)
        top_n: max number of BUY recommendations
        codes: optional list of codes (default: all in watchlist)
        min_credibility: minimum credibility ("高" / "中" / "低")
        min_margin: minimum margin% to be considered

    Returns:
        dict with buy_list / sell_list / hold_list / metrics / sector / warnings
    """
    if codes is None:
        from lib import watchlist_store
        wl = watchlist_store.list_all()
        if wl.empty:
            return _empty_result("自选股为空")
        codes = wl["code"].tolist()

    if not codes:
        return _empty_result("codes 为空")

    try:
        snap = latest_for_codes(codes)
    except Exception as e:
        return _empty_result(f"replica 查询失败: {e}")

    if snap.empty:
        return _empty_result("replica 无 valuation 数据")

    # Compute composite scores
    rows = []
    for _, r in snap.iterrows():
        code = r.get("code")
        rating = r.get("rating") or "D"
        cred = r.get("credibility") or "低"
        margin = float(r.get("margin") or 0)
        intrinsic = float(r.get("intrinsic_value") or 0)
        current = float(r.get("current_price") or 0)
        score = _composite_score(cred, rating, margin)
        rows.append({
            "code": code,
            "name": r.get("name") or code,
            "industry": r.get("industry") or "其他",
            "rating": rating,
            "credibility": cred,
            "margin": margin,
            "intrinsic_value": intrinsic,
            "current_price": current,
            "composite_score": score,
            "data_credibility": CREDIBILITY_SCORE.get(cred, 0),
        })

    df = pd.DataFrame(rows)

    # Sort by composite score desc
    df = df.sort_values("composite_score", ascending=False)

    # Classify into BUY / SELL / HOLD
    min_cred_val = CREDIBILITY_SCORE.get(min_credibility, 0.6)
    buy = df[
        (df["composite_score"] >= 60)
        & (df["data_credibility"] >= min_cred_val)
        & (df["margin"] >= min_margin)
    ]
    sell = df[
        (df["rating"].isin(["D", "F"])) | (df["margin"] < -20)
    ]
    # Hold: rated C or C+ but not qualifying for buy/sell
    hold = df[
        (~df["code"].isin(buy["code"]))
        & (~df["code"].isin(sell["code"]))
    ]

    # Apply top_n to BUY
    buy = buy.head(top_n)

    # Compute target weights (Kelly-ish, capped at 20% per stock)
    if not buy.empty:
        total_score = buy["composite_score"].sum()
        if total_score > 0:
            buy_dict = buy.to_dict("records")
            for h in buy_dict:
                h["target_weight"] = min(0.20, h["composite_score"] / total_score)
                h["target_amount"] = h["target_weight"] * cash_available
        else:
            buy_dict = buy.to_dict("records")
            for h in buy_dict:
                h["target_weight"] = 0
                h["target_amount"] = 0
    else:
        buy_dict = []

    sell_dict = sell.head(20).to_dict("records")
    hold_dict = hold.head(20).to_dict("records")

    # Sector allocation
    sector = {}
    for h in buy_dict:
        sector[h["industry"]] = sector.get(h["industry"], 0) + h.get("target_weight", 0)

    # Portfolio metrics
    metrics = {
        "buy_count": len(buy_dict),
        "sell_count": len(sell_dict),
        "hold_count": len(hold_dict),
        "total_codes": len(codes),
        "avg_score": float(df["composite_score"].mean()) if not df.empty else 0,
        "avg_margin": float(df["margin"].mean()) if not df.empty else 0,
        "top2_concentration": sum(sorted([h.get("target_weight", 0) for h in buy_dict], reverse=True)[:2]),
        "status": "ok" if buy_dict else "no_valid",
    }

    # Risk warnings
    warnings = []
    if not buy_dict:
        warnings.append(
            f"无可信标的 (阈值: composite≥60, credibility≥{min_credibility}, margin≥{min_margin}%)"
        )
    if buy_dict and metrics["top2_concentration"] > 0.5:
        warnings.append(f"Top2 集中度 {metrics['top2_concentration']:.0%} > 50%, 风险偏高")
    if df["margin"].mean() < -20:
        warnings.append(f"自选股平均 margin {df['margin'].mean():.1f}%, 整体高估")

    return {
        "buy_list": buy_dict,
        "sell_list": sell_dict,
        "hold_list": hold_dict,
        "portfolio_metrics": metrics,
        "sector_allocation": sector,
        "risk_warnings": warnings,
    }


def _empty_result(reason: str) -> dict:
    """Return an empty result with reason."""
    return {
        "buy_list": [],
        "sell_list": [],
        "hold_list": [],
        "portfolio_metrics": {"status": "no_valid", "reason": reason, "buy_count": 0, "sell_count": 0, "hold_count": 0},
        "sector_allocation": {},
        "risk_warnings": [reason],
    }


__all__ = ["rank_local", "CREDIBILITY_SCORE", "RATING_SCORE"]
