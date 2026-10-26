import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PROJECT = ROOT.parent.parent / "airport-data-integration"
sys.path.insert(0, str(DB_PROJECT.parent))
from airport_data_integration.database.db import get_connection

FLIGHTS_CSV = ROOT / "data" / "synthetic" / "flights.csv"
ROSTERS_CSV = ROOT / "data" / "synthetic" / "crew_rosters.csv"


def load_crew_rosters():
    with FLIGHTS_CSV.open(encoding="utf-8-sig", newline="") as f:
        flights = {r["flight_id"]: r["flight_number"] for r in csv.DictReader(f)}

    conn = get_connection()
    try:
        staff_rows = conn.execute("SELECT id, staff_name FROM staff").fetchall()
        staff_map = {
            "S" + f"{int(row['staff_name'].split()[-1]):04d}": row["id"]
            for row in staff_rows if row["staff_name"].startswith("Synthetic Staff ")
        }

        inserted = 0
        with ROSTERS_CSV.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                flight_number = flights.get(row["flight_id"])
                flight = conn.execute(
                    "SELECT id FROM flights WHERE flight_number = ?", (flight_number,)
                ).fetchone() if flight_number else None
                staff_id = staff_map.get(row["staff_id"])
                if flight is None:
                    raise ValueError(f"Flight not found: {row['flight_id']}")
                if staff_id is None:
                    raise ValueError(f"Staff not found: {row['staff_id']}")

                conn.execute(
                    """INSERT INTO crew_rosters
                    (flight_id, staff_id, duty_start, duty_end, is_synthetic)
                    VALUES (?, ?, ?, ?, ?)""",
                    (flight["id"], staff_id, row["duty_start"], row["duty_end"], int(row["is_synthetic"]))
                )
                inserted += 1

        conn.commit()
        print("Crew roster records inserted:", inserted)
        print("Total crew rosters in database:", conn.execute("SELECT COUNT(*) FROM crew_rosters").fetchone()[0])
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    load_crew_rosters()
