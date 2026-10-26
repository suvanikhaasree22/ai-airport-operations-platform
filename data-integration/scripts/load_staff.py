"""Load synthetic staff records into SQLite database.

Assignment: Person 3 - Synthetic Operational Data (DI-6)
Resolves airport_id from airports table using home_airport_code.
Idempotent: Checks (airport_id, staff_name) before insertion to avoid duplicates.
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

DEFAULT_CSV_PATH = ROOT / "data" / "synthetic" / "staff.csv"


def load_staff(
    csv_path: Path = DEFAULT_CSV_PATH,
    db_path: Path | None = None,
    dry_run: bool = False,
) -> dict:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Synthetic staff file not found: {csv_path}")

    stats = {"read": 0, "inserted": 0, "skipped": 0, "errors": 0}
    conn = get_connection(db_path)

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))

        stats["read"] = len(rows)

        # Cache airport iata_code -> id
        airport_rows = conn.execute("SELECT id, iata_code FROM airports WHERE iata_code IS NOT NULL").fetchall()
        airport_map = {r["iata_code"].strip().upper(): r["id"] for r in airport_rows}

        for row in rows:
            airport_code = row["home_airport_code"].strip().upper()
            airport_id = airport_map.get(airport_code)

            if airport_id is None:
                raise ValueError(f"Airport not found in DB for staff {row.get('staff_id')}: {airport_code}")

            staff_name = row["staff_name"].strip()
            role = row.get("role", "staff").strip()
            is_synthetic = int(row.get("is_synthetic", 1))

            # Idempotency check
            existing = conn.execute(
                "SELECT id FROM staff WHERE airport_id = ? AND staff_name = ?",
                (airport_id, staff_name),
            ).fetchone()

            if existing:
                stats["skipped"] += 1
                continue

            if not dry_run:
                conn.execute(
                    """
                    INSERT INTO staff
                    (airport_id, staff_name, role, is_synthetic)
                    VALUES (?, ?, ?, ?)
                    """,
                    (airport_id, staff_name, role, is_synthetic),
                )
                stats["inserted"] += 1
            else:
                stats["inserted"] += 1

        if not dry_run:
            conn.commit()

        total_in_db = conn.execute("SELECT COUNT(*) FROM staff").fetchone()[0]
        stats["total_in_db"] = total_in_db

        mode_str = "[DRY-RUN] " if dry_run else ""
        print(f"{mode_str}Staff -> Read: {stats['read']}, Inserted: {stats['inserted']}, Skipped: {stats['skipped']}, Total in DB: {total_in_db}")
        return stats

    except Exception as exc:
        conn.rollback()
        raise RuntimeError(f"Database error loading staff: {exc}") from exc
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load synthetic staff into database.")
    parser.add_argument("--csv-path", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--db-path", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Simulate without committing changes")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        load_staff(args.csv_path, args.db_path, args.dry_run)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
