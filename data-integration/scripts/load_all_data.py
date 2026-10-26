"""Execute full data loading pipeline in correct dependency order.

Dependency order:
  1. airports (master)
  2. runways (master)
  3. gates (synthetic)
  4. flights (synthetic)
  5. gate_bookings (synthetic, depends on flights & gates)
  6. staff (synthetic)
  7. crew_rosters (synthetic, depends on flights & staff)

Supports --dry-run and custom --db-path.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.load_airports import load_airports
from scripts.load_runways import load_runways
from scripts.load_gates import load_gates
from scripts.load_flights import load_flights
from scripts.load_gate_bookings import load_gate_bookings
from scripts.load_staff import load_staff
from scripts.load_crew_rosters import load_crew_rosters


def load_all(db_path: Path | None = None, dry_run: bool = False) -> dict:
    mode = "[DRY-RUN] " if dry_run else ""
    print(f"\n{mode}Executing data loading pipeline in dependency order...\n")

    summary = {}
    loaders = [
        ("airports", load_airports, {}),
        ("runways", load_runways, {}),
        ("gates", load_gates, {}),
        ("flights", load_flights, {}),
        ("gate_bookings", load_gate_bookings, {}),
        ("staff", load_staff, {}),
        ("crew_rosters", load_crew_rosters, {}),
    ]

    for name, loader_fn, kwargs in loaders:
        print(f"--> Loading {name}...")
        res = loader_fn(db_path=db_path, dry_run=dry_run, **kwargs)
        summary[name] = res

    print(f"\n{mode}All datasets processed successfully!")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run complete data loading pipeline in order.")
    parser.add_argument("--db-path", type=Path, default=None, help="Path to SQLite database")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without committing changes")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        load_all(db_path=args.db_path, dry_run=args.dry_run)
    except Exception as exc:
        print(f"\nERROR in pipeline execution: {exc}", file=sys.stderr)
        sys.exit(1)
