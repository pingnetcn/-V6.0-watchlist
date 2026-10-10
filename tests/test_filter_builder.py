import pandas as pd
from lib.filter_builder import apply, SUGGEST_RELAX


def test_apply_margin_gt():
    df = pd.DataFrame({"margin": [10, 30, 50], "rating": ["A", "B", "C"]})
    result = apply(df, {"margin_gt": 20})
    assert len(result) == 2


def test_apply_combined():
    df = pd.DataFrame({
        "margin": [10, 30, 50],
        "rating": ["A", "B", "C"],
        "credibility": ["高", "中", "高"],
    })
    result = apply(df, {"margin_gt": 20, "rating_in": ["A", "B"], "credibility_ge": "中"})
    assert len(result) == 1
    assert result.iloc[0]["rating"] == "B"


def test_suggest_relax_returns_suggestion():
    df = pd.DataFrame({"margin": [10, 30], "rating": ["A", "B"]})
    # 0 result with current filters → suggest relaxing
    suggestion = SUGGEST_RELAX(df, {"margin_gt": 100, "rating_in": ["A+"]})
    assert isinstance(suggestion, str)


def test_apply_failure_mode_count_lt():
    """failure_modes is comma-separated VARCHAR; count = commas + 1 if non-empty."""
    df = pd.DataFrame({
        "failure_modes": ["FM-01,FM-06", "FM-01", "", None, "FM-01,FM-02,FM-03"],
    })
    # failure_modes counts: 2, 1, 0, 0, 3
    result = apply(df, {"failure_mode_count_lt": 2})
    # Expect: rows with count < 2 → "FM-01" (1), "" (0), None (0)
    assert len(result) == 3
    assert "FM-01" in result["failure_modes"].tolist()