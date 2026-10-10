"""
Single-stock Kelly criterion preview — pure local implementation.

Why local (not wrap main project):
    Main project's tradingagents.agents.managers.pm_kelly has deep dep chain
    (langchain_core, yfinance, ...) that conflicts with watchlist's isolation
    principle. Local Kelly is the classic formula; full Phil Town gating can
    be added later if needed.

How to extend:
    Add new position-sizing methods alongside compute_kelly_preview()

Public API:
    compute_kelly_preview(holding) -> dict
"""
from typing import Any

SCHEMA_VERSION = 1


def compute_kelly_preview(holding: dict) -> dict:
    """Compute Kelly fraction + Phil Town conservative factor.

    Args:
        holding: dict with keys (all optional, sensible defaults):
            buy_confidence (0-100): subjective win probability
            rr_val (float): reward/risk ratio (alternative to up/down_pct)
            up_pct (0-100): upside percent
            down_pct (0-100): downside percent
            phil_town_factor (float, optional): override conservative factor

    Returns:
        dict with f_star, position_pct, phil_town_factor
    """
    buy_confidence = holding.get("buy_confidence", 50) / 100.0
    up_pct = holding.get("up_pct", 25) / 100.0
    down_pct = holding.get("down_pct", 15) / 100.0

    # Reward/risk ratio: prefer explicit rr_val, else derive from up/down
    rr_val = holding.get("rr_val")
    if rr_val is not None:
        b = float(rr_val)
    elif down_pct > 0:
        b = up_pct / down_pct
    else:
        b = 1.0

    # Kelly fraction: f* = (bp - q) / b
    # where p = win prob, q = 1 - p, b = odds
    p = buy_confidence
    q = 1.0 - p
    if b > 0:
        f_star = (b * p - q) / b
    else:
        f_star = 0.0

    # Cap Kelly at 25% (industry standard for safety)
    f_star = max(0.0, min(f_star, 0.25))

    # Phil Town gate: half-Kelly as conservative default
    # (real Phil Town uses 0.6/0.8 factors based on conflict between
    # fundamental and technical signals; we use 0.5 for safety)
    phil_town_factor = holding.get("phil_town_factor", 0.5)

    position_pct = f_star * 100.0 * phil_town_factor

    return {
        "f_star": f_star,
        "position_pct": position_pct,
        "phil_town_factor": phil_town_factor,
    }
