"""Generate reproducible synthetic airport-operations CSV data.

Assignment: Person 3 - Synthetic Operational Data (DI-6)
Generates:
  1. Flights (flights.csv)
  2. Gates (gates.csv)
  3. Gate bookings / assignments (gate_bookings.csv)
  4. Airport staff (staff.csv)
  5. Crew rosters (crew_rosters.csv)

All generated entities include `is_synthetic = 1` and satisfy referential
integrity and operational non-overlap constraints.
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Project root defaults to parent of scripts/
DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED_DIR = DEFAULT_ROOT / "data" / "processed"
DEFAULT_OUTPUT_DIR = DEFAULT_ROOT / "data" / "synthetic"

DEFAULT_SEED = 20261026
DEFAULT_NUM_FLIGHTS = 100
DEFAULT_NUM_GATES = 20
DEFAULT_NUM_STAFF = 80
DEFAULT_NUM_BOOKINGS = 100
DEFAULT_NUM_ROSTERS = 200
DEFAULT_BUFFER_MINUTES = 15


def read_csv(path: Path) -> List[Dict[str, str]]:
    """Read CSV file with utf-8-sig encoding and return list of row dictionaries."""
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    """Write list of row dictionaries to CSV with UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"Refusing to write an empty dataset: {path}")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def intervals_overlap(
    start_a: datetime,
    end_a: datetime,
    start_b: datetime,
    end_b: datetime,
    buffer_minutes: int = 0,
) -> bool:
    """Return True if interval A and interval B overlap, accounting for a buffer."""
    buf = timedelta(minutes=buffer_minutes)
    return start_a < (end_b + buf) and start_b < (end_a + buf)


def generate(
    seed: int = DEFAULT_SEED,
    num_flights: int = DEFAULT_NUM_FLIGHTS,
    num_gates: int = DEFAULT_NUM_GATES,
    gates_per_airport: int | None = None,
    num_staff: int = DEFAULT_NUM_STAFF,
    num_bookings: int = DEFAULT_NUM_BOOKINGS,
    num_rosters: int = DEFAULT_NUM_ROSTERS,
    turnaround_buffer_minutes: int = DEFAULT_BUFFER_MINUTES,
    processed_dir: Path = DEFAULT_PROCESSED_DIR,
) -> Dict[str, List[Dict[str, Any]]]:
    """Generate all synthetic operational datasets deterministically."""
    rng = random.Random(seed)

    airports_raw = read_csv(processed_dir / "airports.csv")
    if len(airports_raw) < 2:
        raise ValueError("At least two processed airports are required in airports.csv.")

    # Sort airports deterministically by IATA code for stable generation
    airports = sorted(
        [a for a in airports_raw if a.get("iata_code", "").strip() and a.get("id", "").strip()],
        key=lambda a: a["iata_code"].strip().upper(),
    )
    if len(airports) < 2:
        raise ValueError("airports.csv must contain at least two valid records with numeric id and iata_code.")

    airport_codes = [a["iata_code"].strip().upper() for a in airports]
    airport_id_by_code = {a["iata_code"].strip().upper(): int(a["id"]) for a in airports}

    # 1. Gates
    if gates_per_airport is not None and gates_per_airport > 0:
        actual_num_gates = len(airport_codes) * gates_per_airport
    else:
        actual_num_gates = max(num_gates, len(airport_codes))

    gates: List[Dict[str, Any]] = []
    terminals = ["A", "B", "C", "D"]
    for i in range(1, actual_num_gates + 1):
        airport_code = airport_codes[(i - 1) % len(airport_codes)]
        gate_code = f"G{i:03d}"
        status = "maintenance" if (i % 8 == 0) else "available"
        gates.append({
            "gate_id": gate_code,
            "gate_code": gate_code,
            "airport_id": airport_id_by_code[airport_code],
            "airport_code": airport_code,
            "terminal": terminals[(i - 1) % len(terminals)],
            "gate_status": status,
            "is_synthetic": 1,
        })

    # 2. Flights
    base_time = datetime(2026, 11, 1, 6, 0)
    flights: List[Dict[str, Any]] = []
    used_flight_numbers: Set[str] = set()

    for i in range(1, num_flights + 1):
        origin = rng.choice(airport_codes)
        dest_candidates = [c for c in airport_codes if c != origin]
        dest = rng.choice(dest_candidates)

        # 7-day scheduling window in 15-minute increments
        dep_offset_min = rng.randrange(0, 7 * 24 * 60, 15)
        departure = base_time + timedelta(minutes=dep_offset_min)
        duration_min = rng.randint(60, 360)
        arrival = departure + timedelta(minutes=duration_min)

        # Unique plausible flight number
        while True:
            candidate_fn = f"SN{rng.randint(1000, 9999)}"
            if candidate_fn not in used_flight_numbers:
                used_flight_numbers.add(candidate_fn)
                break

        status = rng.choices(
            ["Scheduled", "Delayed", "On Time"],
            weights=[0.80, 0.15, 0.05],
        )[0]

        flights.append({
            "flight_id": f"F{i:04d}",
            "flight_number": candidate_fn,
            "airline_code": "SN",
            "origin_airport_id": airport_id_by_code[origin],
            "origin_code": origin,
            "destination_airport_id": airport_id_by_code[dest],
            "destination_code": dest,
            "scheduled_departure": departure.isoformat(timespec="minutes"),
            "scheduled_arrival": arrival.isoformat(timespec="minutes"),
            "status": status,
            "is_synthetic": 1,
        })

    # Sort flights chronologically by scheduled departure for deterministic gate and crew scheduling
    flights.sort(key=lambda f: f["scheduled_departure"])

    # 3. Staff
    roles = ["ground_staff", "gate_agent", "baggage_staff", "crew", "pilot", "flight_attendant"]
    staff: List[Dict[str, Any]] = []
    for i in range(1, num_staff + 1):
        airport_code = airport_codes[(i - 1) % len(airport_codes)]
        role = roles[(i - 1) % len(roles)]
        staff.append({
            "staff_id": f"S{i:04d}",
            "staff_name": f"Synthetic Staff {i:03d}",
            "role": role,
            "home_airport_code": airport_code,
            "availability_status": "available",
            "is_synthetic": 1,
        })

    # 4. Gate bookings (conflict-free with turnaround buffer)
    gates_by_airport: Dict[str, List[Dict[str, Any]]] = {}
    for gate in gates:
        gates_by_airport.setdefault(gate["airport_code"], []).append(gate)

    occupied_gate_intervals: Dict[str, List[Tuple[datetime, datetime]]] = {
        g["gate_id"]: [] for g in gates
    }
    gate_bookings: List[Dict[str, Any]] = []

    target_bookings = min(num_bookings, len(flights))
    for flight in flights[:target_bookings]:
        origin = flight["origin_code"]
        dep = datetime.fromisoformat(flight["scheduled_departure"])
        booking_start = dep - timedelta(minutes=45)
        booking_end = dep + timedelta(minutes=30)

        # Primary candidates: gates at origin airport not under maintenance
        airport_gates = gates_by_airport.get(origin, [])
        primary_candidates = [g for g in airport_gates if g["gate_status"] != "maintenance"]
        if not primary_candidates:
            primary_candidates = airport_gates

        chosen_gate = None
        # Try finding a gate with no overlap respecting turnaround buffer
        for gate in primary_candidates:
            intervals = occupied_gate_intervals[gate["gate_id"]]
            if all(
                not intervals_overlap(
                    booking_start, booking_end, existing_start, existing_end, turnaround_buffer_minutes
                )
                for existing_start, existing_end in intervals
            ):
                chosen_gate = gate
                break

        # Fallback: try any gate at the airport without buffer
        if chosen_gate is None:
            for gate in airport_gates:
                intervals = occupied_gate_intervals[gate["gate_id"]]
                if all(
                    not intervals_overlap(booking_start, booking_end, existing_start, existing_end, 0)
                    for existing_start, existing_end in intervals
                ):
                    chosen_gate = gate
                    break

        # Fallback 2: try all gates across system if origin gates are fully booked
        if chosen_gate is None:
            for gate in gates:
                intervals = occupied_gate_intervals[gate["gate_id"]]
                if all(
                    not intervals_overlap(booking_start, booking_end, existing_start, existing_end, 0)
                    for existing_start, existing_end in intervals
                ):
                    chosen_gate = gate
                    break

        if chosen_gate is None:
            raise RuntimeError(
                f"Could not assign a conflict-free gate for flight {flight['flight_id']} at {origin}."
            )

        occupied_gate_intervals[chosen_gate["gate_id"]].append((booking_start, booking_end))
        gate_bookings.append({
            "booking_id": f"B{len(gate_bookings) + 1:04d}",
            "gate_id": chosen_gate["gate_id"],
            "flight_id": flight["flight_id"],
            "booking_start": booking_start.isoformat(timespec="minutes"),
            "booking_end": booking_end.isoformat(timespec="minutes"),
            "is_synthetic": 1,
        })

    # 5. Crew Rosters (conflict-free duty scheduling)
    # Each flight gets 2 crew members until target roster count is reached.
    staff_duty_intervals: Dict[str, List[Tuple[datetime, datetime]]] = {
        s["staff_id"]: [] for s in staff
    }
    crew_rosters: List[Dict[str, Any]] = []

    rosters_per_flight = max(1, num_rosters // len(flights))
    remaining_rosters = num_rosters

    for flight in flights:
        if remaining_rosters <= 0:
            break

        dep = datetime.fromisoformat(flight["scheduled_departure"])
        arr = datetime.fromisoformat(flight["scheduled_arrival"])
        duty_start = dep - timedelta(hours=2)
        duty_end = arr + timedelta(minutes=30)

        needed = min(rosters_per_flight, remaining_rosters)
        # Select staff with least existing assignments to balance workload
        available_staff_candidates = sorted(
            staff,
            key=lambda s: len(staff_duty_intervals[s["staff_id"]]),
        )

        assigned_for_flight: List[Dict[str, Any]] = []
        for candidate in available_staff_candidates:
            cid = candidate["staff_id"]
            intervals = staff_duty_intervals[cid]
            # Check candidate is not on duty during this period
            if all(
                not intervals_overlap(duty_start, duty_end, prev_s, prev_e, 0)
                for prev_s, prev_e in intervals
            ):
                assigned_for_flight.append(candidate)
                if len(assigned_for_flight) == needed:
                    break

        if len(assigned_for_flight) < needed:
            raise RuntimeError(
                f"Insufficient conflict-free staff available for flight {flight['flight_id']}."
            )

        for member in assigned_for_flight:
            staff_duty_intervals[member["staff_id"]].append((duty_start, duty_end))
            crew_rosters.append({
                "roster_id": f"R{len(crew_rosters) + 1:04d}",
                "flight_id": flight["flight_id"],
                "staff_id": member["staff_id"],
                "duty_start": duty_start.isoformat(timespec="minutes"),
                "duty_end": duty_end.isoformat(timespec="minutes"),
                "is_synthetic": 1,
            })
            remaining_rosters -= 1

    datasets = {
        "flights.csv": flights,
        "gates.csv": gates,
        "gate_bookings.csv": gate_bookings,
        "staff.csv": staff,
        "crew_rosters.csv": crew_rosters,
    }

    # Internal validation prior to saving
    validate_in_memory(datasets, airport_id_by_code)
    return datasets


def validate_in_memory(
    datasets: Dict[str, List[Dict[str, Any]]],
    airport_id_by_code: Dict[str, int],
) -> None:
    """Perform strict in-memory consistency checks on generated records."""
    flights = datasets["flights.csv"]
    gates = datasets["gates.csv"]
    bookings = datasets["gate_bookings.csv"]
    staff = datasets["staff.csv"]
    rosters = datasets["crew_rosters.csv"]

    # 1. Check ID uniqueness and synthetic flags
    for name, rows, id_col in [
        ("flights.csv", flights, "flight_id"),
        ("gates.csv", gates, "gate_id"),
        ("gate_bookings.csv", bookings, "booking_id"),
        ("staff.csv", staff, "staff_id"),
        ("crew_rosters.csv", rosters, "roster_id"),
    ]:
        ids = [r[id_col] for r in rows]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate IDs detected in {name} ({id_col}).")
        if any(int(r.get("is_synthetic", 0)) != 1 for r in rows):
            raise ValueError(f"Non-synthetic record found in synthetic dataset {name}.")

    # 2. Flight numbers unique
    fn_set = [f["flight_number"] for f in flights]
    if len(fn_set) != len(set(fn_set)):
        raise ValueError("Duplicate flight numbers generated.")

    # 3. Referential integrity
    airport_ids = set(airport_id_by_code.values())
    flight_ids = {f["flight_id"] for f in flights}
    gate_ids = {g["gate_id"] for g in gates}
    staff_ids = {s["staff_id"] for s in staff}

    for flight in flights:
        if flight["origin_airport_id"] not in airport_ids or flight["destination_airport_id"] not in airport_ids:
            raise ValueError(f"Invalid airport reference in flight {flight['flight_id']}.")
        if flight["origin_code"] == flight["destination_code"]:
            raise ValueError(f"Origin and destination cannot be identical in {flight['flight_id']}.")
        dep = datetime.fromisoformat(flight["scheduled_departure"])
        arr = datetime.fromisoformat(flight["scheduled_arrival"])
        if dep >= arr:
            raise ValueError(f"Departure must precede arrival in flight {flight['flight_id']}.")

    for gate in gates:
        if gate["airport_id"] not in airport_ids:
            raise ValueError(f"Invalid airport reference in gate {gate['gate_id']}.")

    for booking in bookings:
        if booking["flight_id"] not in flight_ids:
            raise ValueError(f"Invalid flight reference in booking {booking['booking_id']}.")
        if booking["gate_id"] not in gate_ids:
            raise ValueError(f"Invalid gate reference in booking {booking['booking_id']}.")
        start = datetime.fromisoformat(booking["booking_start"])
        end = datetime.fromisoformat(booking["booking_end"])
        if start >= end:
            raise ValueError(f"Booking start must precede end in {booking['booking_id']}.")

    for roster in rosters:
        if roster["flight_id"] not in flight_ids:
            raise ValueError(f"Invalid flight reference in roster {roster['roster_id']}.")
        if roster["staff_id"] not in staff_ids:
            raise ValueError(f"Invalid staff reference in roster {roster['roster_id']}.")
        start = datetime.fromisoformat(roster["duty_start"])
        end = datetime.fromisoformat(roster["duty_end"])
        if start >= end:
            raise ValueError(f"Duty start must precede duty end in roster {roster['roster_id']}.")

    # 4. Check gate overlap
    by_gate: Dict[str, List[Tuple[datetime, datetime]]] = {}
    for b in bookings:
        by_gate.setdefault(b["gate_id"], []).append(
            (datetime.fromisoformat(b["booking_start"]), datetime.fromisoformat(b["booking_end"]))
        )
    for gate_id, intervals in by_gate.items():
        intervals.sort()
        for i in range(len(intervals) - 1):
            if intervals_overlap(intervals[i][0], intervals[i][1], intervals[i + 1][0], intervals[i + 1][1], 0):
                raise ValueError(f"Overlapping bookings detected on gate {gate_id}.")

    # 5. Check crew schedule conflict
    by_staff: Dict[str, List[Tuple[datetime, datetime]]] = {}
    for r in rosters:
        by_staff.setdefault(r["staff_id"], []).append(
            (datetime.fromisoformat(r["duty_start"]), datetime.fromisoformat(r["duty_end"]))
        )
    for staff_id, intervals in by_staff.items():
        intervals.sort()
        for i in range(len(intervals) - 1):
            if intervals_overlap(intervals[i][0], intervals[i][1], intervals[i + 1][0], intervals[i + 1][1], 0):
                raise ValueError(f"Overlapping duty schedule detected for staff member {staff_id}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate reproducible synthetic airport operational datasets."
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"Random seed (default: {DEFAULT_SEED})")
    parser.add_argument("--flights", type=int, default=DEFAULT_NUM_FLIGHTS, help="Number of flights (default: 100)")
    parser.add_argument("--gates", type=int, default=DEFAULT_NUM_GATES, help="Number of gates (default: 20)")
    parser.add_argument("--gates-per-airport", type=int, default=None, help="Gates per airport (overrides --gates)")
    parser.add_argument("--staff", type=int, default=DEFAULT_NUM_STAFF, help="Number of staff (default: 80)")
    parser.add_argument("--bookings", type=int, default=DEFAULT_NUM_BOOKINGS, help="Number of bookings (default: 100)")
    parser.add_argument("--crew-rosters", type=int, default=DEFAULT_NUM_ROSTERS, help="Number of rosters (default: 200)")
    parser.add_argument(
        "--turnaround-buffer",
        type=int,
        default=DEFAULT_BUFFER_MINUTES,
        help="Turnaround buffer in minutes between gate bookings (default: 15)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for generated CSVs (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=DEFAULT_PROCESSED_DIR,
        help=f"Processed master data directory (default: {DEFAULT_PROCESSED_DIR})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(f"Generating synthetic operational data (seed={args.seed})...")
    try:
        datasets = generate(
            seed=args.seed,
            num_flights=args.flights,
            num_gates=args.gates,
            gates_per_airport=args.gates_per_airport,
            num_staff=args.staff,
            num_bookings=args.bookings,
            num_rosters=args.crew_rosters,
            turnaround_buffer_minutes=args.turnaround_buffer,
            processed_dir=args.processed_dir,
        )

        args.output_dir.mkdir(parents=True, exist_ok=True)
        print("\nGeneration summary:")
        for filename, rows in datasets.items():
            out_file = args.output_dir / filename
            write_csv(out_file, rows)
            print(f"  - {filename:18}: {len(rows):>4} records -> {out_file}")

        print(f"\nTurnaround buffer used: {args.turnaround_buffer} minutes.")
        print("PASS: Reproducible datasets generated and in-memory consistency verified successfully.")
        return 0
    except Exception as exc:
        print(f"ERROR: Synthetic data generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
