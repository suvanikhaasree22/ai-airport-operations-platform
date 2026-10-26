"""Integration and unit tests for database loaders and idempotency.

Assignment: Person 3 - Synthetic Operational Data (DI-6)
Tests all database loading operations against isolated temporary SQLite instances.
Compatible with both `unittest` and `pytest`.
"""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DB_PROJECT = ROOT / "multi-ai-airport-operations-platform" / "airport-data-integration"
if str(DB_PROJECT) not in sys.path:
    sys.path.insert(0, str(DB_PROJECT))

from scripts.load_airports import load_airports
from scripts.load_runways import load_runways
from scripts.load_gates import load_gates
from scripts.load_flights import load_flights
from scripts.load_gate_bookings import load_gate_bookings
from scripts.load_staff import load_staff
from scripts.load_crew_rosters import load_crew_rosters
from scripts.load_all_data import load_all
from scripts.verify_database import verify_database


class TestDatabaseLoaders(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_operations.db"

        # Initialize schema
        schema_file = DB_PROJECT / "database" / "schema.sql"
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema_file.read_text(encoding="utf-8"))
        conn.commit()
        conn.close()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_dependency_order_loading(self) -> None:
        """Loading dependent tables before parents must fail on foreign key or missing parent."""
        # Attempting to load gates before airports must raise an error
        with self.assertRaises((RuntimeError, ValueError)):
            load_gates(db_path=self.db_path)

    def test_dry_run_mode_does_not_mutate_database(self) -> None:
        """Dry-run execution must report candidate insertions without committing changes."""
        res = load_airports(db_path=self.db_path, dry_run=True)
        self.assertEqual(res["inserted"], 10)

        conn = sqlite3.connect(self.db_path)
        count = conn.execute("SELECT COUNT(*) FROM airports").fetchone()[0]
        conn.close()
        self.assertEqual(count, 0, "Dry-run committed records to database unexpectedly.")

    def test_end_to_end_loading_and_idempotency(self) -> None:
        """Loading all datasets in order must succeed, and second run must insert 0 duplicates."""
        # First execution: loads all records
        summary1 = load_all(db_path=self.db_path, dry_run=False)
        self.assertEqual(summary1["airports"]["inserted"], 10)
        self.assertEqual(summary1["runways"]["inserted"], 55)
        self.assertEqual(summary1["gates"]["inserted"], 20)
        self.assertEqual(summary1["flights"]["inserted"], 100)
        self.assertEqual(summary1["gate_bookings"]["inserted"], 100)
        self.assertEqual(summary1["staff"]["inserted"], 80)
        self.assertEqual(summary1["crew_rosters"]["inserted"], 200)

        # Second execution: idempotency check (all must be skipped)
        summary2 = load_all(db_path=self.db_path, dry_run=False)
        for tbl in ["airports", "runways", "gates", "flights", "gate_bookings", "staff", "crew_rosters"]:
            self.assertEqual(
                summary2[tbl]["inserted"],
                0,
                f"Second loader run inserted duplicate records in {tbl}.",
            )
            self.assertGreater(
                summary2[tbl]["skipped"],
                0,
                f"Second loader run failed to skip existing records in {tbl}.",
            )

    def test_foreign_key_integrity_and_zero_conflicts(self) -> None:
        """Full load must satisfy all database verification checks (10/10 PASS)."""
        load_all(db_path=self.db_path, dry_run=False)
        exit_code = verify_database(db_path=self.db_path, test_idempotency=True)
        self.assertEqual(exit_code, 0, "Database verification reported integrity failures.")

    def test_invalid_database_path_handling(self) -> None:
        """Invalid database directory must raise an appropriate error."""
        invalid_path = Path("/nonexistent/directory/db.sqlite")
        with self.assertRaises(Exception):
            load_airports(db_path=invalid_path)


if __name__ == "__main__":
    unittest.main()
