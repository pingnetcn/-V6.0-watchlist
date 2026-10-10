#!/usr/bin/env bash
# ISOL smoke tests — must pass before each phase delivery.
# Tests verify watchlist app (8910) does not impact main app (8905).

set -e
PASS=0
FAIL=0
WATCHLIST_URL="http://127.0.0.1:8910"
MAIN_URL="http://127.0.0.1:8905"

check() {
    local name="$1"
    local cmd="$2"
    if eval "$cmd" > /dev/null 2>&1; then
        echo "✅ PASS: $name"
        PASS=$((PASS+1))
    else
        echo "❌ FAIL: $name"
        FAIL=$((FAIL+1))
    fi
}

# ISOL-1: Both apps responding
check "ISOL-1a: 8910 HTTP 200" "curl -s -o /dev/null -w '%{http_code}' $WATCHLIST_URL/ | grep -q 200"
check "ISOL-1b: 8905 HTTP 200" "curl -s -o /dev/null -w '%{http_code}' $MAIN_URL/ | grep -q 200"

# ISOL-2: Watchlist DB writes do not affect main DuckDB
# Tested in tests/test_isolation.py (Python fixture, not bash)

echo ""
echo "Results: $PASS passed, $FAIL failed"
exit $FAIL
