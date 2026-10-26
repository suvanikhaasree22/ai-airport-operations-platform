"""Load processed master runway records into SQLite database.

Master data loader for runways table.
Resolves airport_id from airports table using airport_ident.
Idempotent: Skips existing (airport_id, runway_ident) entries.
Supports --dry-run and custom --db-path.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PROJECT = ROOT / "multi-ai-airport-operations-platform" / "airport-data-integration"
if str(DB_PROJECT) not in sys.path:
    sys.path.insert(0, str(DB_PROJECT))

from database.db import get_connection, DB_PATH

DEFAULT_CSV_PATH = ROOT / "data" / "processed" / "runways.csv"


def load_runways(
    csv_path: Path = DEFAULT_CSV_PATH,
    db_path: Path | None = None,
    dry_run: bool = False,
) -> dict:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Processed runways file not found: {csv_path}")

    stats = {"read": 0, "inserted": 0, "skipped": 0, "errors": 0}
    conn = get_connection(db_path)

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))

        stats["read"] = len(rows)

        # Cache airport ident -> id
        airport_rows = conn.execute("SELECT id, ident FROM airports WHERE ident IS NOT NULL").fetchall()
        airport_map = {r["ident"].strip().upper(): r["id"] for r in airport_rows}

        for row in rows:
            ident = row.get("airport_ident", "").strip().upper()
            runway_ident = row.get("le_ident", "").strip() or row.get("runway_ident", "").strip() or None
            length_ft = float(row["length_ft"]) if row.get("length_ft") else None
            width_ft = float(row["width_ft"]) if row.get("width_ft") else None
            surface = row.get("surface", "").strip() or None

            airport_id = airport_map.get(ident)
            if not airport_id:
                raise ValueError(f"Referenced airport ident '{ident}' not found in database.")

            # Idempotency check
            existing = conn.execute(
                "SELECT id FROM runways WHERE airport_id = ? AND runway_ident = ?",
                (airport_id, runway_ident),
            ).fetchone()

            if existing:
                stats["skipped"] += 1
                continue

            if not dry_run:
                conn.execute(
                    """
                    INSERT INTO runways
                    (airport_id, runway_ident, length_ft, width_ft, surface)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (airport_id, runway_ident, length_ft, width_ft, surface),
                )
                stats["inserted"] += 1
            else:
                stats["inserted"] += 1

        if not dry_run:
            conn.commit()

        total_in_db = conn.execute("SELECT COUNT(*) FROM runways").fetchone()[0]
        stats["total_in_db"] = total_in_db

        mode_str = "[DRY-RUN] " if dry_run else ""
        print(f"{mode_str}Runways -> Read: {stats['read']}, Inserted: {stats['inserted']}, Skipped: {stats['skipped']}, Total in DB: {total_in_db}")
        return stats

    except Exception as exc:
        conn.rollback()
        raise RuntimeError(f"Database error loading runways: {exc}") from exc
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load processed runways into database.")
    parser.add_argument("--csv-path", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--db-path", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Simulate without committing changes")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        load_runways(args.csv_path, args.db_path, args.dry_run)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
