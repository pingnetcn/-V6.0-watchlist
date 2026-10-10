"""UI helpers shared across pages.

Why a separate module:
- Avoids forward-reference bugs (helper defined at bottom, used at top)
- Single source of truth for stock option lists
- Testable in isolation
"""
import math
from typing import Iterable
import pandas as pd


def isna(x) -> bool:
    """True if value is None, NaN, or empty string."""
    if x is None:
        return True
    if isinstance(x, float) and math.isnan(x):
        return True
    if isinstance(x, str) and x.strip() == "":
        return True
    return False


def build_stock_options(
    codes: Iterable[str],
    name_map: dict[str, str] | None = None,
) -> list[tuple[str, str]]:
    """Build a list of (display_label, code) tuples sorted by name.

    Args:
        codes: iterable of stock codes
        name_map: optional {code: name} mapping (from replica snapshot)
    Returns:
        [(label, code), ...] sorted by label. If no name, label = code.
    """
    if name_map is None:
        name_map = {}
    options = []
    for c in codes:
        name = name_map.get(c) or ""
        if not isna(name):
            options.append((f"{name} ({c})", c))
        else:
            options.append((c, c))
    options.sort(key=lambda x: x[0])
    return options


def stock_name_map(codes: Iterable[str]) -> dict[str, str]:
    """Get {code: name} from replica. Falls back to empty dict on error."""
    try:
        from lib.db import latest_for_codes
        df = latest_for_codes(list(codes))
        return dict(zip(df["code"], df["name"]))
    except Exception:
        return {c: "" for c in codes}
