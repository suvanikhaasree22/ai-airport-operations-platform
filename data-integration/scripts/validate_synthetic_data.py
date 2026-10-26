"""Comprehensive validation pipeline for synthetic operational data and master references.

Assignment: Person 3 - Synthetic Operational Data (DI-6)

Performs:
  1. Schema validation (file existence, column presence, non-null, data types, timestamp formats, ID uniqueness)
  2. Referential integrity (flight airports, gate airports, booking flight/gate, roster flight/staff, runway airports)
  3. Operational consistency (origin != dest, booking start < end, no gate overlaps, no crew conflicts, synthetic flags)
  4. Reproducibility verification (optional flag --check-reproducibility)

Returns exit code 0 on complete pass, 1 on any failure.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SYNTHETIC_DIR = DEFAULT_ROOT / "data" / "synthetic"
DEFAULT_PROCESSED_DIR = DEFAULT_ROOT / "data" / "processed"

if str(DEFAULT_ROOT) not in sys.path:
    sys.path.insert(0, str(DEFAULT_ROOT))

ISO_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$")


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing required file: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def check_iso_format(ts: str) -> bool:
    if not ts or not ISO_TIMESTAMP_PATTERN.match(ts.strip()):
        return False
    try:
        datetime.fromisoformat(ts.strip())
        return True
    except ValueError:
        return False


def intervals_overlap(s1: datetime, e1: datetime, s2: datetime, e2: datetime) -> bool:
    return s1 < e2 and s2 < e1


class ValidationReporter:
    def __init__(self) -> None:
        self.results: List[Tuple[str, str, str]] = []  # (Category, Description, Status)
        self.has_failure = False

    def report(self, category: str, description: str, passed: bool, detail: str = "") -> None:
        status = "PASS" if passed else "FAIL"
        if not passed:
            self.has_failure = True
        msg = f"{description} - {detail}" if detail else description
        self.results.append((category, msg, status))

    def print_summary(self) -> None:
        print("\n" + "=" * 80)
        print("          SYNTHETIC DATA VALIDATION REPORT (DI-6)")
        print("=" * 80)
        current_cat = ""
        for cat, desc, status in self.results:
            if cat != current_cat:
                print(f"\n[{cat.upper()}]")
                current_cat = cat
            badge = "[ PASS ]" if status == "PASS" else "[ FAIL ]"
            print(f"  {badge} {desc}")
        print("-" * 80)
        total = len(self.results)
        passed = sum(1 for _, _, s in self.results if s == "PASS")
        failed = sum(1 for _, _, s in self.results if s == "FAIL")
        print(f"Summary: {total} checks executed | {passed} PASSED | {failed} FAILED")
        print("=" * 80)


def validate_synthetic_datasets(
    synthetic_dir: Path,
    processed_dir: Path,
    reporter: ValidationReporter,
) -> None:
    # 1. Master files existence
    airports_path = processed_dir / "airports.csv"
    runways_path = processed_dir / "runways.csv"
    reporter.report(
        "File Presence",
        "Master data files exist (airports.csv, runways.csv)",
        airports_path.is_file() and runways_path.is_file(),
    )

    if not airports_path.is_file() or not runways_path.is_file():
        reporter.report("File Presence", "Aborting remaining checks due to missing master data", False)
        return

    airports = read_csv(airports_path)
    runways = read_csv(runways_path)

    # 2. Synthetic files existence
    expected_files = ["flights.csv", "gates.csv", "gate_bookings.csv", "staff.csv", "crew_rosters.csv"]
    all_files_present = True
    for fname in expected_files:
        p = synthetic_dir / fname
        present = p.is_file()
        reporter.report("File Presence", f"Synthetic file {fname} exists", present)
        if not present:
            all_files_present = False

    if not all_files_present:
        reporter.report("File Presence", "Aborting remaining checks due to missing synthetic files", False)
        return

    flights = read_csv(synthetic_dir / "flights.csv")
    gates = read_csv(synthetic_dir / "gates.csv")
    bookings = read_csv(synthetic_dir / "gate_bookings.csv")
    staff = read_csv(synthetic_dir / "staff.csv")
    rosters = read_csv(synthetic_dir / "crew_rosters.csv")

    # Record counts
    reporter.report(
        "Schema Validation",
        "Record counts",
        len(flights) > 0 and len(gates) > 0 and len(bookings) > 0 and len(staff) > 0 and len(rosters) > 0,
        f"flights={len(flights)}, gates={len(gates)}, bookings={len(bookings)}, staff={len(staff)}, rosters={len(rosters)}",
    )

    # Required columns
    expected_cols = {
        "flights.csv": ["flight_id", "flight_number", "origin_code", "destination_code", "scheduled_departure", "scheduled_arrival", "is_synthetic"],
        "gates.csv": ["gate_id", "airport_code", "is_synthetic"],
        "gate_bookings.csv": ["booking_id", "gate_id", "flight_id", "booking_start", "booking_end", "is_synthetic"],
        "staff.csv": ["staff_id", "staff_name", "role", "home_airport_code", "is_synthetic"],
        "crew_rosters.csv": ["roster_id", "flight_id", "staff_id", "duty_start", "duty_end", "is_synthetic"],
    }
    data_map = {
        "flights.csv": flights,
        "gates.csv": gates,
        "gate_bookings.csv": bookings,
        "staff.csv": staff,
        "crew_rosters.csv": rosters,
    }

    for fname, req_cols in expected_cols.items():
        rows = data_map[fname]
        if rows:
            actual_cols = set(rows[0].keys())
            missing = set(req_cols) - actual_cols
            reporter.report(
                "Schema Validation",
                f"Required columns in {fname}",
                len(missing) == 0,
                f"missing: {missing}" if missing else "all present",
            )

    # Check non-null / non-empty in mandatory columns
    for fname, rows in data_map.items():
        empty_count = 0
        for r in rows:
            for c in expected_cols[fname]:
                if r.get(c) is None or str(r.get(c)).strip() == "":
                    empty_count += 1
        reporter.report(
            "Schema Validation",
            f"No empty mandatory fields in {fname}",
            empty_count == 0,
            f"{empty_count} blank cells found" if empty_count else "no missing values",
        )

    # Primary key uniqueness
    for fname, rows, id_col in [
        ("flights.csv", flights, "flight_id"),
        ("flights.csv", flights, "flight_number"),
        ("gates.csv", gates, "gate_id"),
        ("gate_bookings.csv", bookings, "booking_id"),
        ("staff.csv", staff, "staff_id"),
        ("crew_rosters.csv", rosters, "roster_id"),
    ]:
        vals = [r[id_col].strip() for r in rows if r.get(id_col)]
        unique = len(vals) == len(set(vals))
        reporter.report(
            "Schema Validation",
            f"Unique identifiers for {fname} ({id_col})",
            unique,
            f"count={len(vals)}, unique={len(set(vals))}",
        )

    # Timestamp format validation
    flight_dep_valid = all(check_iso_format(f["scheduled_departure"]) for f in flights)
    flight_arr_valid = all(check_iso_format(f["scheduled_arrival"]) for f in flights)
    booking_start_valid = all(check_iso_format(b["booking_start"]) for b in bookings)
    booking_end_valid = all(check_iso_format(b["booking_end"]) for b in bookings)
    roster_start_valid = all(check_iso_format(r["duty_start"]) for r in rosters)
    roster_end_valid = all(check_iso_format(r["duty_end"]) for r in rosters)

    all_ts_valid = (
        flight_dep_valid
        and flight_arr_valid
        and booking_start_valid
        and booking_end_valid
        and roster_start_valid
        and roster_end_valid
    )
    reporter.report(
        "Schema Validation",
        "Timestamp formats follow ISO 8601 (YYYY-MM-DDTHH:MM)",
        all_ts_valid,
    )

    # Synthetic flag check
    for fname, rows in data_map.items():
        all_syn = all(str(r.get("is_synthetic", "")).strip() == "1" for r in rows)
        reporter.report(
            "Operational Consistency",
            f"All records have is_synthetic = 1 in {fname}",
            all_syn,
        )

    # Referential Integrity: Airports and Runways master data
    airport_ids = {str(a["id"]).strip() for a in airports if a.get("id")}
    airport_iatas = {a["iata_code"].strip().upper() for a in airports if a.get("iata_code")}

    runway_orphans = [r for r in runways if str(r.get("airport_ref", "")).strip() not in airport_ids]
    reporter.report(
        "Referential Integrity",
        "Master runway references to airports",
        len(runway_orphans) == 0,
        f"{len(runway_orphans)} orphaned runways" if runway_orphans else f"all {len(runways)} runways valid",
    )

    # Referential Integrity: Flights to Airports
    flight_origin_valid = all(f["origin_code"].strip().upper() in airport_iatas for f in flights)
    flight_dest_valid = all(f["destination_code"].strip().upper() in airport_iatas for f in flights)
    reporter.report(
        "Referential Integrity",
        "Flight origin and destination airport references",
        flight_origin_valid and flight_dest_valid,
    )

    # Referential Integrity: Gates to Airports
    gate_airport_valid = all(g["airport_code"].strip().upper() in airport_iatas for g in gates)
    reporter.report(
        "Referential Integrity",
        "Gate airport references",
        gate_airport_valid,
    )

    # Referential Integrity: Staff to Airports
    staff_airport_valid = all(s["home_airport_code"].strip().upper() in airport_iatas for s in staff)
    reporter.report(
        "Referential Integrity",
        "Staff home airport references",
        staff_airport_valid,
    )

    # Referential Integrity: Bookings to Flights and Gates
    flight_id_set = {f["flight_id"].strip() for f in flights}
    gate_id_set = {g["gate_id"].strip() for g in gates}
    staff_id_set = {s["staff_id"].strip() for s in staff}

    booking_flights_valid = all(b["flight_id"].strip() in flight_id_set for b in bookings)
    booking_gates_valid = all(b["gate_id"].strip() in gate_id_set for b in bookings)
    reporter.report(
        "Referential Integrity",
        "Gate booking flight and gate references",
        booking_flights_valid and booking_gates_valid,
    )

    # Referential Integrity: Crew Rosters to Flights and Staff
    roster_flights_valid = all(r["flight_id"].strip() in flight_id_set for r in rosters)
    roster_staff_valid = all(r["staff_id"].strip() in staff_id_set for r in rosters)
    reporter.report(
        "Referential Integrity",
        "Crew roster flight and staff references",
        roster_flights_valid and roster_staff_valid,
    )

    # Operational Consistency: Flights origin != destination
    flight_diff_endpoints = all(f["origin_code"].strip().upper() != f["destination_code"].strip().upper() for f in flights)
    reporter.report(
        "Operational Consistency",
        "Flight origin differs from destination",
        flight_diff_endpoints,
    )

    # Operational Consistency: Flight departure < arrival
    flight_order_valid = all(
        datetime.fromisoformat(f["scheduled_departure"].strip()) < datetime.fromisoformat(f["scheduled_arrival"].strip())
        for f in flights
    )
    reporter.report(
        "Operational Consistency",
        "Flight scheduled departure precedes arrival",
        flight_order_valid,
    )

    # Operational Consistency: Booking start < end
    booking_order_valid = all(
        datetime.fromisoformat(b["booking_start"].strip()) < datetime.fromisoformat(b["booking_end"].strip())
        for b in bookings
    )
    reporter.report(
        "Operational Consistency",
        "Gate booking start time precedes end time",
        booking_order_valid,
    )

    # Operational Consistency: Gate overlap check
    by_gate: Dict[str, List[Tuple[datetime, datetime, str]]] = {}
    for b in bookings:
        by_gate.setdefault(b["gate_id"].strip(), []).append(
            (
                datetime.fromisoformat(b["booking_start"].strip()),
                datetime.fromisoformat(b["booking_end"].strip()),
                b["booking_id"].strip(),
            )
        )

    gate_conflicts: List[str] = []
    for gid, intervals in by_gate.items():
        intervals.sort(key=lambda x: x[0])
        for i in range(len(intervals) - 1):
            if intervals_overlap(intervals[i][0], intervals[i][1], intervals[i + 1][0], intervals[i + 1][1]):
                gate_conflicts.append(f"Gate {gid}: {intervals[i][2]} overlaps with {intervals[i+1][2]}")

    reporter.report(
        "Operational Consistency",
        "Zero gate-booking overlaps on the same gate",
        len(gate_conflicts) == 0,
        f"{len(gate_conflicts)} conflicts detected" if gate_conflicts else "0 overlaps",
    )

    # Operational Consistency: Crew duty start < end
    roster_order_valid = all(
        datetime.fromisoformat(r["duty_start"].strip()) < datetime.fromisoformat(r["duty_end"].strip())
        for r in rosters
    )
    reporter.report(
        "Operational Consistency",
        "Crew roster duty start precedes duty end",
        roster_order_valid,
    )

    # Operational Consistency: No duplicate crew assignments per flight
    roster_pairs = [(r["flight_id"].strip(), r["staff_id"].strip()) for r in rosters]
    unique_roster_pairs = len(roster_pairs) == len(set(roster_pairs))
    reporter.report(
        "Operational Consistency",
        "No duplicate staff assignments on the same flight",
        unique_roster_pairs,
    )

    # Operational Consistency: Crew schedule conflicts (overlapping duties for same staff)
    by_staff: Dict[str, List[Tuple[datetime, datetime, str]]] = {}
    for r in rosters:
        by_staff.setdefault(r["staff_id"].strip(), []).append(
            (
                datetime.fromisoformat(r["duty_start"].strip()),
                datetime.fromisoformat(r["duty_end"].strip()),
                r["roster_id"].strip(),
            )
        )

    crew_conflicts: List[str] = []
    for sid, intervals in by_staff.items():
        intervals.sort(key=lambda x: x[0])
        for i in range(len(intervals) - 1):
            if intervals_overlap(intervals[i][0], intervals[i][1], intervals[i + 1][0], intervals[i + 1][1]):
                crew_conflicts.append(f"Staff {sid}: {intervals[i][2]} overlaps with {intervals[i+1][2]}")

    reporter.report(
        "Operational Consistency",
        "Zero crew schedule overlaps for the same staff member",
        len(crew_conflicts) == 0,
        f"{len(crew_conflicts)} conflicts detected" if crew_conflicts else "0 conflicts",
    )


def verify_reproducibility(
    seed: int,
    processed_dir: Path,
    reporter: ValidationReporter,
) -> None:
    """Run generation twice in temporary directories and compare file hashes."""
    from scripts.generate_synthetic_data import generate, write_csv
    import hashlib

    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        dir1 = Path(tmp1)
        dir2 = Path(tmp2)

        data1 = generate(seed=seed, processed_dir=processed_dir)
        for fname, rows in data1.items():
            write_csv(dir1 / fname, rows)

        data2 = generate(seed=seed, processed_dir=processed_dir)
        for fname, rows in data2.items():
            write_csv(dir2 / fname, rows)

        identical = True
        for fname in data1.keys():
            h1 = hashlib.sha256((dir1 / fname).read_bytes()).hexdigest()
            h2 = hashlib.sha256((dir2 / fname).read_bytes()).hexdigest()
            if h1 != h2:
                identical = False
                break

        reporter.report(
            "Reproducibility",
            f"Deterministic generation verified across runs (seed={seed})",
            identical,
            "Byte-for-byte identical output" if identical else "Hash mismatch between runs",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate synthetic operational datasets and master data references."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_SYNTHETIC_DIR,
        help=f"Synthetic data directory to validate (default: {DEFAULT_SYNTHETIC_DIR})",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=DEFAULT_PROCESSED_DIR,
        help=f"Processed master data directory (default: {DEFAULT_PROCESSED_DIR})",
    )
    parser.add_argument(
        "--check-reproducibility",
        action="store_true",
        help="Run reproducibility verification test with fixed seed",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20261026,
        help="Seed to use for reproducibility test (default: 20261026)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    reporter = ValidationReporter()

    print(f"Validating synthetic operational data in: {args.data_dir}")
    print(f"Referencing processed master data in:    {args.processed_dir}")

    validate_synthetic_datasets(args.data_dir, args.processed_dir, reporter)

    if args.check_reproducibility:
        verify_reproducibility(args.seed, args.processed_dir, reporter)

    reporter.print_summary()
    return 1 if reporter.has_failure else 0


if __name__ == "__main__":
    sys.exit(main())
