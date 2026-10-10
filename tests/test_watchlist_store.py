import pytest
import tempfile
import os
from lib import watchlist_store


@pytest.fixture(autouse=True)
def tmp_db(monkeypatch):
    """Each test gets a fresh SQLite file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_path = f.name
    monkeypatch.setattr(watchlist_store, "DB_PATH", __import__("pathlib").Path(tmp_path))
    # Reset module-level connection if any
    watchlist_store._init_schema()
    yield tmp_path
    os.unlink(tmp_path)


def test_add_and_list():
    assert watchlist_store.add("000999", note="华润三九") is True
    df = watchlist_store.list_all()
    assert "000999" in df["code"].values
    assert df[df["code"] == "000999"]["note"].iloc[0] == "华润三九"


def test_remove():
    watchlist_store.add("000999")
    assert watchlist_store.remove("000999") is True
    assert "000999" not in watchlist_store.list_all()["code"].values


def test_remove_nonexistent_returns_false():
    assert watchlist_store.remove("999999") is False


def test_update_tags():
    watchlist_store.add("000999")
    assert watchlist_store.update_tags("000999", ["白酒", "医药"]) is True
    import json
    df = watchlist_store.list_all()
    assert json.loads(df[df["code"] == "000999"]["tags"].iloc[0]) == ["白酒", "医药"]


def test_audit_log_capture():
    watchlist_store.add("000999", note="test")
    audit = watchlist_store.get_audit_log(code="000999")
    assert len(audit) >= 1
    assert audit.iloc[0]["action"] == "add"


def test_import_codes_bulk():
    n = watchlist_store.import_codes(["000999", "000858", "600519"])
    assert n == 3
    df = watchlist_store.list_all()
    assert len(df) == 3


def test_schema_version_2_has_tags_column():
    watchlist_store._init_schema()
    import sqlite3
    conn = sqlite3.connect(str(watchlist_store.DB_PATH))
    cols = [r[1] for r in conn.execute("PRAGMA table_info(watchlist)").fetchall()]
    assert "tags" in cols
    conn.close()
