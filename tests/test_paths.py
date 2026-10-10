from lib.paths import MAIN_PROJECT, DB_PATH, VAL_REPORTS_DIR, get_main_project

def test_main_project_path_exists():
    assert MAIN_PROJECT.exists(), f"Main project not found at {MAIN_PROJECT}"

def test_db_path_is_duckdb():
    assert str(DB_PATH).endswith(".duckdb")

def test_val_reports_dir_exists():
    assert VAL_REPORTS_DIR.exists(), f"Val reports dir not found at {VAL_REPORTS_DIR}"

def test_get_main_project_returns_path():
    assert get_main_project() == MAIN_PROJECT