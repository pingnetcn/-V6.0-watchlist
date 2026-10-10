from pathlib import Path
from lib.completeness import score_one, score_batch

FIXTURE = Path(__file__).parent.parent / "fixtures" / "val_000999_v18.txt"


def test_score_one_returns_dict():
    result = score_one(FIXTURE)
    assert "credibility_score" in result or "credibility_tier" in result
    assert "quality_grade" in result


def test_score_batch_returns_dataframe():
    import pandas as pd
    df = score_batch(["000999"])
    assert isinstance(df, pd.DataFrame)
