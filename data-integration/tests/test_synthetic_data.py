"""Unit tests for synthetic operational data generator and validation logic.

Assignment: Person 3 - Synthetic Operational Data (DI-6)
Compatible with both `unittest` and `pytest`.
"""
from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_synthetic_data import generate, intervals_overlap, write_csv
from scripts.validate_synthetic_data import ValidationReporter, validate_synthetic_datasets


class TestSyntheticDataGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.processed_dir = ROOT / "data" / "processed"
        cls.seed = 20261026
        cls.data = generate(seed=cls.seed, processed_dir=cls.processed_dir)

    def test_deterministic_generation_fixed_seed(self) -> None:
        """Generating twice with identical seed and inputs must yield identical data."""
        data_second_run = generate(seed=self.seed, processed_dir=self.processed_dir)
        self.assertEqual(len(self.data), len(data_second_run))
        for key in self.data:
            self.assertEqual(
                self.data[key],
                data_second_run[key],
                f"Dataset {key} differed between runs with identical seed.",
            )

    def test_different_seeds_produce_different_data(self) -> None:
        """Different seeds must produce different operational schedules."""
        data_other_seed = generate(seed=99999, processed_dir=self.processed_dir)
        self.assertNotEqual(
            [f["flight_number"] for f in self.data["flights.csv"]],
            [f["flight_number"] for f in data_other_seed["flights.csv"]],
        )

    def test_correct_csv_headers(self) -> None:
        """Generated datasets must include expected schema columns."""
        expected_columns = {
            "flights.csv": {"flight_id", "flight_number", "origin_code", "destination_code", "scheduled_departure", "scheduled_arrival", "status", "is_synthetic"},
            "gates.csv": {"gate_id", "gate_code", "airport_code", "terminal", "gate_status", "is_synthetic"},
            "gate_bookings.csv": {"booking_id", "gate_id", "flight_id", "booking_start", "booking_end", "is_synthetic"},
            "staff.csv": {"staff_id", "staff_name", "role", "home_airport_code", "availability_status", "is_synthetic"},
            "crew_rosters.csv": {"roster_id", "flight_id", "staff_id", "duty_start", "duty_end", "is_synthetic"},
        }
        for filename, expected_set in expected_columns.items():
            rows = self.data[filename]
            self.assertGreater(len(rows), 0, f"{filename} has 0 records.")
            actual_set = set(rows[0].keys())
            self.assertTrue(
                expected_set.issubset(actual_set),
                f"Missing expected columns in {filename}: {expected_set - actual_set}",
            )

    def test_unique_identifiers(self) -> None:
        """Primary IDs must be unique across all entities."""
        for filename, id_key in [
            ("flights.csv", "flight_id"),
            ("flights.csv", "flight_number"),
            ("gates.csv", "gate_id"),
            ("gate_bookings.csv", "booking_id"),
            ("staff.csv", "staff_id"),
            ("crew_rosters.csv", "roster_id"),
        ]:
            ids = [r[id_key] for r in self.data[filename]]
            self.assertEqual(len(ids), len(set(ids)), f"Duplicate {id_key} found in {filename}.")

    def test_valid_airport_references(self) -> None:
        """Flights, gates, and staff must only reference valid processed airports."""
        with (self.processed_dir / "airports.csv").open("r", encoding="utf-8-sig") as f:
            valid_iatas = {r["iata_code"].strip().upper() for r in csv.DictReader(f) if r.get("iata_code")}

        for f in self.data["flights.csv"]:
            self.assertIn(f["origin_code"].upper(), valid_iatas)
            self.assertIn(f["destination_code"].upper(), valid_iatas)

        for g in self.data["gates.csv"]:
            self.assertIn(g["airport_code"].upper(), valid_iatas)

        for s in self.data["staff.csv"]:
            self.assertIn(s["home_airport_code"].upper(), valid_iatas)

    def test_valid_flight_and_gate_references(self) -> None:
        """Bookings and rosters must reference valid flights, gates, and staff."""
        flight_ids = {f["flight_id"] for f in self.data["flights.csv"]}
        gate_ids = {g["gate_id"] for g in self.data["gates.csv"]}
        staff_ids = {s["staff_id"] for s in self.data["staff.csv"]}

        for b in self.data["gate_bookings.csv"]:
            self.assertIn(b["flight_id"], flight_ids)
            self.assertIn(b["gate_id"], gate_ids)

        for r in self.data["crew_rosters.csv"]:
            self.assertIn(r["flight_id"], flight_ids)
            self.assertIn(r["staff_id"], staff_ids)

    def test_flight_origin_destination_distinct(self) -> None:
        """A flight cannot depart from and arrive at the same airport."""
        for f in self.data["flights.csv"]:
            self.assertNotEqual(
                f["origin_code"],
                f["destination_code"],
                f"Flight {f['flight_id']} has identical origin and destination.",
            )

    def test_booking_start_precedes_end(self) -> None:
        """Booking start time must precede end time."""
        for b in self.data["gate_bookings.csv"]:
            start = datetime.fromisoformat(b["booking_start"])
            end = datetime.fromisoformat(b["booking_end"])
            self.assertLess(start, end, f"Booking {b['booking_id']} has invalid time order.")

    def test_zero_gate_overlaps(self) -> None:
        """No two bookings on the same gate may overlap."""
        by_gate: dict[str, list[tuple[datetime, datetime, str]]] = {}
        for b in self.data["gate_bookings.csv"]:
            by_gate.setdefault(b["gate_id"], []).append(
                (
                    datetime.fromisoformat(b["booking_start"]),
                    datetime.fromisoformat(b["booking_end"]),
                    b["booking_id"],
                )
            )

        for gate_id, intervals in by_gate.items():
            intervals.sort(key=lambda x: x[0])
            for i in range(len(intervals) - 1):
                self.assertFalse(
                    intervals_overlap(intervals[i][0], intervals[i][1], intervals[i + 1][0], intervals[i + 1][1]),
                    f"Gate {gate_id} booking overlap: {intervals[i][2]} and {intervals[i+1][2]}",
                )

    def test_zero_crew_schedule_conflicts(self) -> None:
        """No staff member may be scheduled for overlapping duty periods."""
        by_staff: dict[str, list[tuple[datetime, datetime, str]]] = {}
        for r in self.data["crew_rosters.csv"]:
            by_staff.setdefault(r["staff_id"], []).append(
                (
                    datetime.fromisoformat(r["duty_start"]),
                    datetime.fromisoformat(r["duty_end"]),
                    r["roster_id"],
                )
            )

        for staff_id, intervals in by_staff.items():
            intervals.sort(key=lambda x: x[0])
            for i in range(len(intervals) - 1):
                self.assertFalse(
                    intervals_overlap(intervals[i][0], intervals[i][1], intervals[i + 1][0], intervals[i + 1][1]),
                    f"Staff {staff_id} duty overlap: {intervals[i][2]} and {intervals[i+1][2]}",
                )

    def test_synthetic_flag_handling(self) -> None:
        """Every generated operational row must have is_synthetic = 1."""
        for filename in ["flights.csv", "gates.csv", "gate_bookings.csv", "staff.csv", "crew_rosters.csv"]:
            for row in self.data[filename]:
                self.assertEqual(int(row["is_synthetic"]), 1, f"Missing is_synthetic=1 in {filename}")

    def test_missing_required_input_handling(self) -> None:
        """Missing input directory or file must raise FileNotFoundError."""
        with tempfile.TemporaryDirectory() as empty_dir:
            with self.assertRaises(FileNotFoundError):
                generate(processed_dir=Path(empty_dir))

    def test_invalid_source_data_handling(self) -> None:
        """Processed airports with fewer than 2 records must raise ValueError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "airports.csv").write_text("id,iata_code,name\n1,ATL,Atlanta\n", encoding="utf-8")
            (tmp_path / "runways.csv").write_text("id,airport_ref,airport_ident\n1,1,KATL\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                generate(processed_dir=tmp_path)


if __name__ == "__main__":
    unittest.main()
