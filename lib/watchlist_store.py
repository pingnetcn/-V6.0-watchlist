"""
SQLite CRUD for watchlist + audit log.

How to extend:
    New field? Add via _migrate() with new SCHEMA_VERSION, use ALTER TABLE ADD COLUMN
    New action type? Add to ACTION_TYPES constant

Public API:
    add(code, note=None, tags=None) -> bool
    remove(code) -> bool
    list_all(active_only=True) -> DataFrame
    update_note(code, note) -> bool
    update_tags(code, tags: list[str]) -> bool
    audit_log(action, code, details) -> None
    get_audit_log(code=None, limit=100) -> DataFrame
    import_codes(codes, source='candidate_pool') -> int
    clear_all() -> int
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional
import pandas as pd

SCHEMA_VERSION = 2
DB_PATH = Path(__file__).parent.parent / "data" / "watchlist.db"
ACTION_TYPES = {"add", "remove", "update_note", "update_tags", "import", "clear"}

_schema_initialized = False


def _ensure_schema():
    """Lazy init: schema is created on first connection, not at module import.

    Allows tests to monkeypatch DB_PATH before any DB file is touched.
    Idempotent — safe to call multiple times.
    """
    global _schema_initialized
    if _schema_initialized:
        return
    # Set flag BEFORE calling _init_schema so that _init_schema -> _get_conn ->
    # _ensure_schema re-entry is a no-op (would otherwise recurse infinitely).
    _schema_initialized = True
    _init_schema()


def _get_conn() -> sqlite3.Connection:
    _ensure_schema()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _init_schema():
    conn = _get_conn()
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    if current < 1:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                code VARCHAR PRIMARY KEY,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                note TEXT,
                target_weight REAL,
                active BOOLEAN DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action VARCHAR NOT NULL,
                code VARCHAR,
                details TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_active ON watchlist(active)")
    if current < 2:
        conn.execute("ALTER TABLE watchlist ADD COLUMN tags TEXT")
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()
    conn.close()


def audit_log(action: str, code: Optional[str], details: dict) -> None:
    if action not in ACTION_TYPES:
        raise ValueError(f"Unknown action: {action}")
    conn = _get_conn()
    conn.execute(
        "INSERT INTO audit_log (action, code, details) VALUES (?, ?, ?)",
        (action, code, json.dumps(details, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


def add(code: str, note: Optional[str] = None, tags: Optional[list[str]] = None) -> bool:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO watchlist (code, note, tags) VALUES (?, ?, ?)",
            (code, note, json.dumps(tags or [], ensure_ascii=False)),
        )
        conn.commit()
        audit_log("add", code, {"note": note, "tags": tags or []})
        return True
    finally:
        conn.close()


def remove(code: str) -> bool:
    conn = _get_conn()
    cur = conn.execute("DELETE FROM watchlist WHERE code = ?", (code,))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected:
        audit_log("remove", code, {})
    return affected > 0


def list_all(active_only: bool = True) -> pd.DataFrame:
    conn = _get_conn()
    sql = "SELECT * FROM watchlist"
    if active_only:
        sql += " WHERE active = 1"
    sql += " ORDER BY added_at DESC"
    df = pd.read_sql(sql, conn)
    conn.close()
    return df


def update_note(code: str, note: str) -> bool:
    conn = _get_conn()
    cur = conn.execute("UPDATE watchlist SET note = ? WHERE code = ?", (note, code))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected:
        audit_log("update_note", code, {"note": note})
    return affected > 0


def update_tags(code: str, tags: list[str]) -> bool:
    conn = _get_conn()
    cur = conn.execute(
        "UPDATE watchlist SET tags = ? WHERE code = ?",
        (json.dumps(tags, ensure_ascii=False), code),
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected:
        audit_log("update_tags", code, {"tags": tags})
    return affected > 0


def get_audit_log(code: Optional[str] = None, limit: int = 100) -> pd.DataFrame:
    conn = _get_conn()
    sql = "SELECT * FROM audit_log"
    params = []
    if code:
        sql += " WHERE code = ?"
        params.append(code)
    sql += " ORDER BY ts DESC LIMIT ?"
    params.append(limit)
    df = pd.read_sql(sql, conn, params=params)
    conn.close()
    return df


def import_codes(codes: list[str], source: str = "candidate_pool") -> int:
    n = 0
    for code in codes:
        if add(code, note=f"imported from {source}"):
            n += 1
    audit_log("import", None, {"count": n, "source": source})
    return n


def clear_all() -> int:
    conn = _get_conn()
    cur = conn.execute("DELETE FROM watchlist")
    conn.commit()
    n = cur.rowcount
    conn.close()
    audit_log("clear", None, {"deleted": n})
    return n
