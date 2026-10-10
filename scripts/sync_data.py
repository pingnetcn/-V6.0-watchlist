"""sync_data.py — 3-step orchestration: stop main 8905 -> run sync -> restart 8905.

Why: main project holds DuckDB with exclusive locks (db_core.py monkey-patch +
_kline.py long write conns). Watchlist's read_only opens fail. We briefly
stop main, copy data, restart main.

Usage:
    python -m scripts.sync_data            # full orchestration
    python -m scripts.sync_data --no-restart  # stop + sync, leave main stopped
    python -m scripts.sync_data --no-stop    # just sync (will fail if main is busy)
"""
import os
import sys
import time
import signal
import subprocess
import argparse
import urllib.request
from pathlib import Path

# Force UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("gbk"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Paths (Windows paths with backslashes; use raw strings)
WATCHLIST_DIR = Path(r"E:\CCTest\陈氏鉴股V6.0-watchlist")
MAIN_DIR = Path(r"E:\CCTest\陈氏鉴股V6.0-v697")
MAIN_PYTHON = str(MAIN_DIR / ".venv_dev" / "Scripts" / "python.exe")
WATCHLIST_PYTHON = str(WATCHLIST_DIR / ".venv" / "Scripts" / "python.exe")


def http_status(url: str, timeout: int = 5) -> int:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status
    except Exception:
        return 0


def find_pid_on_port(port: int) -> int | None:
    """Find the PID listening on a port via netstat."""
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"],
            text=True, encoding="gbk", errors="replace",
        )
    except Exception:
        return None
    for line in out.splitlines():
        if f":{port}" in line and "LISTENING" in line:
            parts = line.split()
            try:
                return int(parts[-1])
            except (ValueError, IndexError):
                continue
    return None


def stop_main() -> bool:
    """Stop main 8905 streamlit. Returns True if stopped or wasn't running."""
    pid = find_pid_on_port(8905)
    if pid is None:
        print("  [skip] 8905 not running")
        return True
    try:
        subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            check=True, capture_output=True, text=True,
        )
        print(f"  [OK] Killed main streamlit (PID {pid})")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  [FAIL] taskkill: {e}")
        return False


def run_sync() -> bool:
    """Run scripts/sync_watchlist_data. Returns True on success."""
    print(f"  Working dir: {WATCHLIST_DIR}")
    print(f"  Python: {WATCHLIST_PYTHON}")
    try:
        result = subprocess.run(
            [WATCHLIST_PYTHON, "-m", "scripts.sync_watchlist_data"],
            cwd=str(WATCHLIST_DIR),
            timeout=180,  # 3 min hard cap
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("  [FAIL] Sync timed out (>3 min)")
        return False
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def start_main() -> bool:
    """Start main 8905 streamlit in background."""
    try:
        subprocess.Popen(
            [MAIN_PYTHON, "-m", "streamlit", "run", "web/app.py",
             "--server.address", "0.0.0.0", "--server.port", "8905",
             "--server.headless", "true"],
            cwd=str(MAIN_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,  # Windows: no console
        )
        print("  [OK] Main streamlit launching (background)")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def wait_for_port(port: int, timeout: int = 30) -> int:
    """Poll HTTP until port responds. Returns status code (0 if timeout)."""
    start = time.time()
    while time.time() - start < timeout:
        status = http_status(f"http://127.0.0.1:{port}/")
        if status == 200:
            return status
        time.sleep(1)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Sync main DuckDB -> watchlist replica")
    parser.add_argument("--no-stop", action="store_true",
                        help="Skip stopping main (sync will likely fail if main is busy)")
    parser.add_argument("--no-restart", action="store_true",
                        help="Skip restarting main at the end")
    parser.add_argument("--skip-verify", action="store_true",
                        help="Skip HTTP verification of both ports")
    args = parser.parse_args()

    print("=" * 60)
    print("  Sync Data Orchestration")
    print(f"  Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    sync_ok = False

    if not args.no_stop:
        print("[1/3] Stop main 8905 to release DuckDB lock...")
        if not stop_main():
            print("  [WARN] Stop failed; sync will likely fail")
        # Give main a moment to fully release the file
        time.sleep(2)
        print()
    else:
        print("[1/3] Skipped (--no-stop)")
        print()

    print("[2/3] Run sync from main -> replica...")
    sync_ok = run_sync()
    print()

    if not args.no_restart:
        print("[3/3] Restart main 8905...")
        if start_main():
            if not args.skip_verify:
                print("  Waiting for main to be ready (up to 30s)...")
                status = wait_for_port(8905, timeout=30)
                if status == 200:
                    print("  [OK] Main responding on 8905")
                else:
                    print("  [WARN] Main not responding within 30s (check manually)")
        print()
    else:
        print("[3/3] Skipped (--no-restart)")
        print()

    if not args.skip_verify:
        print("=" * 60)
        print("  Verification")
        print("=" * 60)
        main_status = http_status("http://127.0.0.1:8905/")
        watch_status = http_status("http://127.0.0.1:8910/")
        print(f"  8905 (main):      HTTP {main_status}")
        print(f"  8910 (watchlist): HTTP {watch_status}")
        print()

    print("=" * 60)
    if sync_ok:
        print(f"  [OK] Sync complete. {time.strftime('%H:%M:%S')}")
        print("  Watchlist at: http://127.0.0.1:8910/")
    else:
        print(f"  [FAIL] Sync did not succeed. Check output above.")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
