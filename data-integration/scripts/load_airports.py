"""Load processed master airport records into SQLite database.

Master data loader for airports table.
Idempotent: Uses UNIQUE(ident) and INSERT OR IGNORE to prevent duplicate rows.
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

DEFAULT_CSV_PATH = ROOT / "data" / "processed" / "airports.csv"


def load_airports(
    csv_path: Path = DEFAULT_CSV_PATH,
    db_path: Path | None = None,
    dry_run: bool = False,
) -> dict:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Processed airports file not found: {csv_path}")

    stats = {"read": 0, "inserted": 0, "skipped": 0, "errors": 0}
    conn = get_connection(db_path)

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))

        stats["read"] = len(rows)

        for row in rows:
            ident = row.get("ident", "").strip() or None
            name = row.get("name", "").strip()
            iata = row.get("iata_code", "").strip().upper() or None
            icao = row.get("icao_code", "").strip().upper() or None
            lat = float(row["latitude_deg"]) if row.get("latitude_deg") else None
            lon = float(row["longitude_deg"]) if row.get("longitude_deg") else None
            country = row.get("iso_country", "").strip() or None

            if not name or not iata:
                stats["skipped"] += 1
                continue

            # Check if record already exists by ident or iata_code
            existing = conn.execute(
                "SELECT id FROM airports WHERE ident = ? OR iata_code = ?",
                (ident, iata),
            ).fetchone()

            if existing:
                stats["skipped"] += 1
                continue

            if not dry_run:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO airports
                    (ident, name, iata_code, icao_code, latitude, longitude, country)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (ident, name, iata, icao, lat, lon, country),
                )
                if conn.execute("SELECT changes()").fetchone()[0] > 0:
                    stats["inserted"] += 1
                else:
                    stats["skipped"] += 1
            else:
                stats["inserted"] += 1

        if not dry_run:
            conn.commit()

        total_in_db = conn.execute("SELECT COUNT(*) FROM airports").fetchone()[0]
        stats["total_in_db"] = total_in_db

        mode_str = "[DRY-RUN] " if dry_run else ""
        print(f"{mode_str}Airports -> Read: {stats['read']}, Inserted: {stats['inserted']}, Skipped: {stats['skipped']}, Total in DB: {total_in_db}")
        return stats

    except Exception as exc:
        conn.rollback()
        raise RuntimeError(f"Database error loading airports: {exc}") from exc
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load processed airports into database.")
    parser.add_argument("--csv-path", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--db-path", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Simulate without committing changes")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        load_airports(args.csv_path, args.db_path, args.dry_run)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
