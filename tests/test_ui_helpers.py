"""Tests for lib/ui_helpers.py — stock option list building."""
from lib.ui_helpers import isna, build_stock_options, stock_name_map


def test_isna_handles_none():
    assert isna(None) is True


def test_isna_handles_nan():
    assert isna(float("nan")) is True


def test_isna_handles_empty_string():
    assert isna("") is True
    assert isna("   ") is True


def test_isna_handles_valid_values():
    assert isna(0) is False
    assert isna("hello") is False
    assert isna(123.45) is False
    assert isna(False) is False


def test_build_stock_options_with_names():
    codes = ["600519", "000858"]
    name_map = {"600519": "贵州茅台", "000858": "五粮液"}
    options = build_stock_options(codes, name_map)
    assert options == [
        ("五粮液 (000858)", "000858"),
        ("贵州茅台 (600519)", "600519"),
    ]


def test_build_stock_options_without_names():
    codes = ["600519", "000858"]
    options = build_stock_options(codes, name_map={})
    # Without names, label == code; sorted alphabetically ("000858" < "600519")
    assert options == [("000858", "000858"), ("600519", "600519")]


def test_build_stock_options_partial_names():
    codes = ["600519", "000858", "000001"]
    name_map = {"600519": "贵州茅台", "000001": "平安银行"}
    options = build_stock_options(codes, name_map)
    labels = [label for label, _ in options]
    # "000858" has no name — should be just the code
    assert "000858" in labels
    assert "平安银行 (000001)" in labels
    assert "贵州茅台 (600519)" in labels


def test_build_stock_options_sorted_by_label():
    codes = ["999999", "000001", "500000"]
    name_map = {"999999": "Zzz", "000001": "Aaa", "500000": "Mmm"}
    options = build_stock_options(codes, name_map)
    labels = [l for l, _ in options]
    assert labels == sorted(labels)


def test_stock_name_map_returns_dict():
    """Test it returns a dict (may be empty if replica unavailable)."""
    result = stock_name_map(["600519"])
    assert isinstance(result, dict)
