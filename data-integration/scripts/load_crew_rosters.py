"""Load synthetic crew rosters into SQLite database.

Assignment: Person 3 - Synthetic Operational Data (DI-6)
Resolves flight_id and staff_id from database tables using stable identifiers.
Idempotent: Checks (flight_id, staff_id) before insertion to avoid duplicates.
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

DEFAULT_ROSTERS_CSV = ROOT / "data" / "synthetic" / "crew_rosters.csv"
DEFAULT_FLIGHTS_CSV = ROOT / "data" / "synthetic" / "flights.csv"
DEFAULT_STAFF_CSV = ROOT / "data" / "synthetic" / "staff.csv"


def load_crew_rosters(
    rosters_csv: Path = DEFAULT_ROSTERS_CSV,
    flights_csv: Path = DEFAULT_FLIGHTS_CSV,
    staff_csv: Path = DEFAULT_STAFF_CSV,
    db_path: Path | None = None,
    dry_run: bool = False,
) -> dict:
    if not rosters_csv.is_file():
        raise FileNotFoundError(f"Synthetic crew rosters file not found: {rosters_csv}")
    if not flights_csv.is_file():
        raise FileNotFoundError(f"Synthetic flights file not found: {flights_csv}")
    if not staff_csv.is_file():
        raise FileNotFoundError(f"Synthetic staff file not found: {staff_csv}")

    stats = {"read": 0, "inserted": 0, "skipped": 0, "errors": 0}
    conn = get_connection(db_path)

    try:
        # Load mappings from synthetic CSV files
        with flights_csv.open("r", encoding="utf-8-sig", newline="") as f:
            flight_id_to_num = {
                row["flight_id"].strip(): row["flight_number"].strip()
                for row in csv.DictReader(f)
            }

        with staff_csv.open("r", encoding="utf-8-sig", newline="") as f:
            staff_id_to_name = {
                row["staff_id"].strip(): row["staff_name"].strip()
                for row in csv.DictReader(f)
            }

        with rosters_csv.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))

        stats["read"] = len(rows)

        # Cache flight_number -> id and staff_name -> id from DB
        flight_rows = conn.execute("SELECT id, flight_number FROM flights").fetchall()
        flight_db_map = {r["flight_number"].strip(): r["id"] for r in flight_rows}

        staff_rows = conn.execute("SELECT id, staff_name FROM staff").fetchall()
        staff_db_map = {r["staff_name"].strip(): r["id"] for r in staff_rows}

        for row in rows:
            flight_synthetic_id = row["flight_id"].strip()
            staff_synthetic_id = row["staff_id"].strip()
            duty_start = row["duty_start"].strip()
            duty_end = row["duty_end"].strip()
            is_synthetic = int(row.get("is_synthetic", 1))

            flight_num = flight_id_to_num.get(flight_synthetic_id)
            if not flight_num:
                raise ValueError(f"Flight ID {flight_synthetic_id} missing from flights CSV")

            staff_name = staff_id_to_name.get(staff_synthetic_id)
            if not staff_name:
                raise ValueError(f"Staff ID {staff_synthetic_id} missing from staff CSV")

            db_flight_id = flight_db_map.get(flight_num)
            if not db_flight_id:
                raise ValueError(f"Flight {flight_num} not found in database for roster {row.get('roster_id')}")

            db_staff_id = staff_db_map.get(staff_name)
            if not db_staff_id:
                raise ValueError(f"Staff '{staff_name}' not found in database for roster {row.get('roster_id')}")

            # Idempotency check: prevent duplicate assignment of staff to flight
            existing = conn.execute(
                """
                SELECT id FROM crew_rosters
                WHERE flight_id = ? AND staff_id = ?
                """,
                (db_flight_id, db_staff_id),
            ).fetchone()

            if existing:
                stats["skipped"] += 1
                continue

            if not dry_run:
                conn.execute(
                    """
                    INSERT INTO crew_rosters
                    (flight_id, staff_id, duty_start, duty_end, is_synthetic)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (db_flight_id, db_staff_id, duty_start, duty_end, is_synthetic),
                )
                stats["inserted"] += 1
            else:
                stats["inserted"] += 1

        if not dry_run:
            conn.commit()

        total_in_db = conn.execute("SELECT COUNT(*) FROM crew_rosters").fetchone()[0]
        stats["total_in_db"] = total_in_db

        mode_str = "[DRY-RUN] " if dry_run else ""
        print(f"{mode_str}Crew Rosters -> Read: {stats['read']}, Inserted: {stats['inserted']}, Skipped: {stats['skipped']}, Total in DB: {total_in_db}")
        return stats

    except Exception as exc:
        conn.rollback()
        raise RuntimeError(f"Database error loading crew rosters: {exc}") from exc
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load synthetic crew rosters into database.")
    parser.add_argument("--csv-path", type=Path, default=DEFAULT_ROSTERS_CSV)
    parser.add_argument("--flights-csv", type=Path, default=DEFAULT_FLIGHTS_CSV)
    parser.add_argument("--staff-csv", type=Path, default=DEFAULT_STAFF_CSV)
    parser.add_argument("--db-path", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Simulate without committing changes")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        load_crew_rosters(args.csv_path, args.flights_csv, args.staff_csv, args.db_path, args.dry_run)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
