from lib.pm_kelly_wrap import compute_kelly_preview


def test_compute_kelly_returns_dict():
    result = compute_kelly_preview({
        "buy_confidence": 70,
        "rr_val": 2.5,
        "up_pct": 30,
        "down_pct": 12,
    })
    assert "f_star" in result or "position_pct" in result
