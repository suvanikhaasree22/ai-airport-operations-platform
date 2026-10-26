"""Load synthetic flights into SQLite database.

Assignment: Person 3 - Synthetic Operational Data (DI-6)
Resolves origin_airport_id and destination_airport_id from airports table.
Idempotent: Uses UNIQUE(flight_number) to prevent duplicate flights.
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

DEFAULT_CSV_PATH = ROOT / "data" / "synthetic" / "flights.csv"


def load_flights(
    csv_path: Path = DEFAULT_CSV_PATH,
    db_path: Path | None = None,
    dry_run: bool = False,
) -> dict:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Synthetic flights file not found: {csv_path}")

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
            flight_num = row["flight_number"].strip()
            origin_code = row["origin_code"].strip().upper()
            dest_code = row["destination_code"].strip().upper()

            origin_id = airport_map.get(origin_code)
            dest_id = airport_map.get(dest_code)

            if origin_id is None:
                raise ValueError(f"Origin airport not found in DB for flight {flight_num}: {origin_code}")
            if dest_id is None:
                raise ValueError(f"Destination airport not found in DB for flight {flight_num}: {dest_code}")

            scheduled_time = row["scheduled_departure"].strip()
            status = row.get("status", "Scheduled").strip().capitalize()
            is_synthetic = int(row.get("is_synthetic", 1))

            # Idempotency check
            existing = conn.execute(
                "SELECT id FROM flights WHERE flight_number = ?",
                (flight_num,),
            ).fetchone()

            if existing:
                stats["skipped"] += 1
                continue

            if not dry_run:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO flights
                    (flight_number, origin_airport_id, destination_airport_id, scheduled_time, status, is_synthetic)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (flight_num, origin_id, dest_id, scheduled_time, status, is_synthetic),
                )
                if conn.execute("SELECT changes()").fetchone()[0] > 0:
                    stats["inserted"] += 1
                else:
                    stats["skipped"] += 1
            else:
                stats["inserted"] += 1

        if not dry_run:
            conn.commit()

        total_in_db = conn.execute("SELECT COUNT(*) FROM flights").fetchone()[0]
        stats["total_in_db"] = total_in_db

        mode_str = "[DRY-RUN] " if dry_run else ""
        print(f"{mode_str}Flights -> Read: {stats['read']}, Inserted: {stats['inserted']}, Skipped: {stats['skipped']}, Total in DB: {total_in_db}")
        return stats

    except Exception as exc:
        conn.rollback()
        raise RuntimeError(f"Database error loading flights: {exc}") from exc
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load synthetic flights into database.")
    parser.add_argument("--csv-path", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--db-path", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Simulate without committing changes")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        load_flights(args.csv_path, args.db_path, args.dry_run)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
