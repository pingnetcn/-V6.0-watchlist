from pathlib import Path
from streamlit.testing.v1 import AppTest

PAGES_DIR = Path(__file__).parent.parent / "pages"


def test_page_1_renders_empty_state():
    at = AppTest.from_file(str(PAGES_DIR / "1_📊_自选股.py")).run()
    assert not at.exception
    assert "自选股" in str(at.title[0].value)


def test_page_2_renders_title():
    at = AppTest.from_file(str(PAGES_DIR / "2_📈_单股深读.py")).run()
    assert not at.exception


def test_page_5_renders_title_only():
    """Page 5 depends on lib.portfolio → ReportRanker (main project).
    AppTest cannot mock main-project deps, so just verify the title renders
    without triggering rank()."""
    at = AppTest.from_file(str(PAGES_DIR / "5_🎯_买卖推荐.py")).run()
    assert not at.exception
    assert "买卖推荐" in str(at.title[0].value)
