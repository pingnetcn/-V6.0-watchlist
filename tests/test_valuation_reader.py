from pathlib import Path
from lib.valuation_reader import parse_metadata, parse_full_report, read_credibility_emoji

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def test_parse_metadata_v18_json():
    meta = parse_metadata(FIXTURE_DIR / "val_000999_v18.txt")
    assert meta["code"] == "000999"
    assert meta["version"] == "v18"
    assert meta["rating"] == "A"
    assert meta["intrinsic_value"] > 0


def test_parse_metadata_v3_fallback():
    meta = parse_metadata(FIXTURE_DIR / "val_000999_v3.txt")
    assert meta["code"] == "000999"
    assert "intrinsic_value" in meta or "valuation_intrinsic" in meta


def test_parse_full_report_v18_has_7_sections():
    result = parse_full_report(FIXTURE_DIR / "val_000999_v18.txt")
    assert "metadata" in result
    assert "sections" in result
    assert len(result["sections"]) >= 7


def test_credibility_emoji():
    assert read_credibility_emoji({"credibility": "高", "credibility_emoji": "🟢"}) == "🟢"
    assert read_credibility_emoji({}) == "❓"
