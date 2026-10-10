"""
Single-stock Kelly criterion preview (wraps pm_kelly).
"""
import sys
from lib.paths import MAIN_PROJECT
if str(MAIN_PROJECT) not in sys.path:
    sys.path.insert(0, str(MAIN_PROJECT))

from tradingagents.agents.managers.pm_kelly import build_kelly_blocks, KellyInput

SCHEMA_VERSION = 1


def compute_kelly_preview(holding: dict) -> dict:
    inp = KellyInput(
        buy_confidence=holding.get("buy_confidence", 50),
        rr_val=holding.get("rr_val", 2.0),
        rr_source=holding.get("rr_source", "默认(无风控校准R/R)"),
        up_pct=holding.get("up_pct", 25),
        down_pct=holding.get("down_pct", 15),
        target_px=holding.get("target_px", 0),
        entry_px=holding.get("entry_px", 0),
        stop_px=holding.get("stop_px", 0),
        dim1_tier=holding.get("dim1_tier", 3),
        rr_tier=holding.get("rr_tier", 3),
    )
    out = build_kelly_blocks(inp)
    return {
        "f_star": getattr(out, "f_star", 0),
        "position_pct": getattr(out, "position_pct", 0),
        "phil_town_factor": getattr(out, "phil_town_factor", 1.0),
    }
