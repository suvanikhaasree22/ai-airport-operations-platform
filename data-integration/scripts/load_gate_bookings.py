"""Load synthetic gate bookings into SQLite database.

Assignment: Person 3 - Synthetic Operational Data (DI-6)
Resolves flight_id and gate_id from database tables using stable identifiers.
Idempotent: Checks (flight_id, gate_id, start_time) before insertion to avoid duplicates.
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

DEFAULT_BOOKINGS_CSV = ROOT / "data" / "synthetic" / "gate_bookings.csv"
DEFAULT_FLIGHTS_CSV = ROOT / "data" / "synthetic" / "flights.csv"


def load_gate_bookings(
    bookings_csv: Path = DEFAULT_BOOKINGS_CSV,
    flights_csv: Path = DEFAULT_FLIGHTS_CSV,
    db_path: Path | None = None,
    dry_run: bool = False,
) -> dict:
    if not bookings_csv.is_file():
        raise FileNotFoundError(f"Synthetic gate bookings file not found: {bookings_csv}")
    if not flights_csv.is_file():
        raise FileNotFoundError(f"Synthetic flights file not found: {flights_csv}")

    stats = {"read": 0, "inserted": 0, "skipped": 0, "errors": 0}
    conn = get_connection(db_path)

    try:
        # Load flight_id -> flight_number mapping from synthetic flights CSV
        with flights_csv.open("r", encoding="utf-8-sig", newline="") as f:
            flight_id_to_num = {
                row["flight_id"].strip(): row["flight_number"].strip()
                for row in csv.DictReader(f)
            }

        with bookings_csv.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))

        stats["read"] = len(rows)

        # Cache flights (flight_number -> id) and gates (gate_code -> id)
        flight_rows = conn.execute("SELECT id, flight_number FROM flights").fetchall()
        flight_db_map = {r["flight_number"].strip(): r["id"] for r in flight_rows}

        gate_rows = conn.execute("SELECT id, gate_code FROM gates").fetchall()
        gate_db_map = {r["gate_code"].strip(): r["id"] for r in gate_rows}

        for row in rows:
            flight_synthetic_id = row["flight_id"].strip()
            gate_code = row["gate_id"].strip()
            booking_start = row["booking_start"].strip()
            booking_end = row["booking_end"].strip()
            is_synthetic = int(row.get("is_synthetic", 1))

            flight_num = flight_id_to_num.get(flight_synthetic_id)
            if not flight_num:
                raise ValueError(f"Unknown flight_id {flight_synthetic_id} in booking {row.get('booking_id')}")

            db_flight_id = flight_db_map.get(flight_num)
            if not db_flight_id:
                raise ValueError(f"Flight {flight_num} not found in database for booking {row.get('booking_id')}")

            db_gate_id = gate_db_map.get(gate_code)
            if not db_gate_id:
                raise ValueError(f"Gate {gate_code} not found in database for booking {row.get('booking_id')}")

            # Idempotency check
            existing = conn.execute(
                """
                SELECT id FROM gate_bookings
                WHERE flight_id = ? AND gate_id = ? AND start_time = ?
                """,
                (db_flight_id, db_gate_id, booking_start),
            ).fetchone()

            if existing:
                stats["skipped"] += 1
                continue

            if not dry_run:
                conn.execute(
                    """
                    INSERT INTO gate_bookings
                    (flight_id, gate_id, start_time, end_time, is_synthetic)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (db_flight_id, db_gate_id, booking_start, booking_end, is_synthetic),
                )
                stats["inserted"] += 1
            else:
                stats["inserted"] += 1

        if not dry_run:
            conn.commit()

        total_in_db = conn.execute("SELECT COUNT(*) FROM gate_bookings").fetchone()[0]
        stats["total_in_db"] = total_in_db

        mode_str = "[DRY-RUN] " if dry_run else ""
        print(f"{mode_str}Gate Bookings -> Read: {stats['read']}, Inserted: {stats['inserted']}, Skipped: {stats['skipped']}, Total in DB: {total_in_db}")
        return stats

    except Exception as exc:
        conn.rollback()
        raise RuntimeError(f"Database error loading gate bookings: {exc}") from exc
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load synthetic gate bookings into database.")
    parser.add_argument("--csv-path", type=Path, default=DEFAULT_BOOKINGS_CSV)
    parser.add_argument("--flights-csv", type=Path, default=DEFAULT_FLIGHTS_CSV)
    parser.add_argument("--db-path", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Simulate without committing changes")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        load_gate_bookings(args.csv_path, args.flights_csv, args.db_path, args.dry_run)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
