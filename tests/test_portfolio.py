from lib.portfolio import rank, format_markdown


def test_rank_returns_three_lists():
    """Smoke test: rank() should return dict with buy/sell/hold keys."""
    result = rank(cash_available=5_000_000, top_n=5, since_date=None)
    assert "buy_list" in result or "buy" in result
    assert "sell_list" in result or "sell" in result
    assert "hold_list" in result or "hold" in result
    assert "portfolio_metrics" in result or "metrics" in result
