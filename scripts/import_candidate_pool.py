"""import_candidate_pool.py — Import candidate stocks from replica into watchlist.

Pulls all distinct stock codes from replica.valuation_history (those with
recent valuations) and adds them to watchlist.db via watchlist_store.import_codes.

Usage:
    python -m scripts.import_candidate_pool                    # default: last 30 days
    python -m scripts.import_candidate_pool --days 7          # last 7 days
    python -m scripts.import_candidate_pool --min-rating A   # only A+ or A
    python -m scripts.import_candidate_pool --clear           # clear watchlist first
    python -m scripts.import_candidate_pool --dry-run        # don't actually add
"""
import sys
import io
import argparse
from datetime import date, timedelta
import duckdb
import pandas as pd

# Force UTF-8 stdout
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("gbk"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Allow imports
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from lib.paths import DB_PATH  # noqa: E402
from lib import watchlist_store  # noqa: E402

REPLICA_PATH = __import__("pathlib").Path(DB_PATH).parent / ".watchlist_data.duckdb"

DEFAULT_DAYS = 30
RATING_ORDER = {"F": 0, "D": 1, "C": 2, "C+": 3, "B": 4, "B+": 5, "A": 6, "A+": 7}


def get_candidate_codes(days: int, min_rating: str | None) -> pd.DataFrame:
    """Get distinct codes with recent valuations, optionally filtered by rating.

    Filters out codes that don't exist in main's stock_basic (test/placeholder
    codes like 600000-600008 that have valuations but no real company data).
    """
    if not REPLICA_PATH.exists():
        print(f"[FAIL] Replica not found: {REPLICA_PATH}")
        print("       Run sync first: python -m scripts.sync_data")
        sys.exit(1)

    conn = duckdb.connect(str(REPLICA_PATH), read_only=True)
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    sql = """
        SELECT
            code,
            name,
            industry,
            company_type,
            rating,
            margin,
            intrinsic_value,
            current_price,
            valuation_date
        FROM (
            SELECT *,
                ROW_NUMBER() OVER (PARTITION BY code ORDER BY valuation_date DESC) AS rn
            FROM valuation_history
            WHERE valuation_date >= ?
        )
        WHERE rn = 1
        ORDER BY code
    """
    df = conn.execute(sql, [cutoff]).df()

    # Filter: only keep codes that exist in main's stock_basic (real companies)
    try:
        real_codes = set(conn.execute(
            "SELECT code FROM stock_basic WHERE code IS NOT NULL"
        ).df()["code"].astype(str).tolist())
        before = len(df)
        df = df[df["code"].astype(str).isin(real_codes)]
        filtered = before - len(df)
        if filtered:
            print(f"  Filtered {filtered} codes not in main stock_basic (test/placeholder)")
    except Exception as e:
        print(f"  [WARN] Could not filter by stock_basic: {e}")

    conn.close()

    # Apply rating filter if specified
    if min_rating and min_rating in RATING_ORDER:
        threshold = RATING_ORDER[min_rating]
        df = df[df["rating"].map(lambda r: RATING_ORDER.get(r, -1) >= threshold)]

    return df


def import_to_watchlist(df: pd.DataFrame, dry_run: bool, clear_first: bool) -> dict:
    """Add candidates to watchlist. Returns stats."""
    if clear_first and not dry_run:
        deleted = watchlist_store.clear_all()
        print(f"  Cleared {deleted} existing watchlist entries")

    codes = df["code"].tolist()
    if dry_run:
        return {"would_add": len(codes), "added": 0, "skipped": 0}

    n = watchlist_store.import_codes(codes, source="candidate_pool")
    return {"would_add": len(codes), "added": n, "skipped": len(codes) - n}


def main():
    parser = argparse.ArgumentParser(description="Import candidate stocks from replica into watchlist")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                        help=f"Only import stocks with valuation in last N days (default {DEFAULT_DAYS})")
    parser.add_argument("--min-rating", type=str, default=None,
                        choices=list(RATING_ORDER.keys()),
                        help="Filter by minimum rating (e.g., 'B' for B+ and above)")
    parser.add_argument("--clear", action="store_true",
                        help="Clear existing watchlist before importing")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be imported without modifying watchlist")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of imports (e.g., --limit 20 for top 20)")
    args = parser.parse_args()

    print("=" * 60)
    print(f"  Import Candidate Pool to Watchlist")
    print(f"  Filter: last {args.days} days"
          + (f", rating >= {args.min_rating}" if args.min_rating else ""))
    print("=" * 60)
    print()

    df = get_candidate_codes(args.days, args.min_rating)
    print(f"  Found {len(df)} candidate stocks")

    if df.empty:
        print("  No candidates. Try increasing --days or check replica contents.")
        sys.exit(0)

    # Show preview
    print()
    print("  Preview (first 10):")
    print("  " + "-" * 56)
    print(f"  {'Code':<8} {'Name':<14} {'Rating':<5} {'Margin':>8} {'Date':<10}")
    print("  " + "-" * 56)
    for _, row in df.head(10).iterrows():
        name = (row.get("name") or "?")[:12]
        rating = row.get("rating") or "?"
        margin = row.get("margin") or 0
        dt = str(row.get("valuation_date") or "")[:10]
        print(f"  {row['code']:<8} {name:<14} {rating:<5} {margin:>+7.1f}% {dt:<10}")
    if len(df) > 10:
        print(f"  ... and {len(df) - 10} more")
    print()

    if args.limit:
        df = df.head(args.limit)
        print(f"  Limited to {args.limit}")

    stats = import_to_watchlist(df, args.dry_run, args.clear)

    print()
    print("=" * 60)
    if args.dry_run:
        print(f"  [DRY RUN] Would add {stats['would_add']} stocks")
    else:
        print(f"  [OK] Added {stats['added']} stocks, skipped {stats['skipped']}")
        if stats["added"] > 0:
            print(f"  Open http://127.0.0.1:8910/ to see them in your watchlist")
    print("=" * 60)


if __name__ == "__main__":
    main()
