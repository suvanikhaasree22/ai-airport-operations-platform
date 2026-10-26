# Airport Operations Coordination Engine — Data Integration (DI-6)
## Person 3: Synthetic Operational Data Pipeline

This repository component implements the complete, reproducible synthetic operational data pipeline and master data integration for the Airport Operations Coordination Engine (DI-6).

---

## 1. Scope and Responsibilities

Person 3 (DI-6) is responsible for generating, validating, loading, and verifying synthetic operational datasets alongside the existing airport and runway master data:
1. **Flights** (`flights.csv` -> `flights` table)
2. **Gates** (`gates.csv` -> `gates` table)
3. **Gate bookings / assignments** (`gate_bookings.csv` -> `gate_bookings` table)
4. **Airport staff** (`staff.csv` -> `staff` table)
5. **Crew rosters** (`crew_rosters.csv` -> `crew_rosters` table)

All synthetic records explicitly include `is_synthetic = 1` and satisfy:
- Full referential integrity against processed airport master data.
- Zero gate-booking interval overlaps on any gate (with configurable turnaround buffer).
- Zero crew schedule duty overlaps for any staff member.
- True idempotency across repeated database loader executions.

---

## 2. Directory Structure

```text
Data-Integration/
├── data/
│   ├── raw/                               # Raw source datasets (never overwritten)
│   │   ├── airports.csv                   # OurAirports master data
│   │   ├── airports_selected.csv          # 10 target internship airport IATA codes
│   │   └── runways.csv                    # OurAirports runway data
│   ├── processed/                         # Cleaned master datasets
│   │   ├── airports.csv                   # 10 selected airports
│   │   └── runways.csv                    # 55 runways belonging to selected airports
│   └── synthetic/                         # Generated synthetic operational datasets
│       ├── flights.csv                    # 100 flights (SN prefix, ISO timestamps)
│       ├── gates.csv                      # 20 gates across 10 airports
│       ├── gate_bookings.csv              # 100 conflict-free gate allocations
│       ├── staff.csv                      # 80 synthetic airport and crew staff
│       └── crew_rosters.csv               # 200 conflict-free flight crew assignments
├── multi-ai-airport-operations-platform/
│   └── airport-data-integration/
│       ├── database/
│       │   ├── schema.sql                 # SQLite schema with foreign key constraints
│       │   ├── db.py                      # Connection helper with foreign keys enabled
│       │   ├── init_db.py                 # Database initialization script
│       │   └── airport_operations.db      # Operational SQLite database
│       └── check_db.py                    # Table discovery helper
├── scripts/
│   ├── clean_airports.py                  # Step 2: Master data cleaning pipeline
│   ├── generate_synthetic_data.py         # Step 3 & 4: Deterministic synthetic generator
│   ├── validate_synthetic_data.py         # Step 5: Comprehensive validator (43 checks)
│   ├── load_airports.py                   # Step 6: Master airport loader
│   ├── load_runways.py                    # Step 6: Master runway loader
│   ├── load_gates.py                      # Step 6: Synthetic gate loader
│   ├── load_flights.py                    # Step 6: Synthetic flight loader
│   ├── load_gate_bookings.py              # Step 6: Synthetic gate booking loader
│   ├── load_staff.py                      # Step 6: Synthetic staff loader
│   ├── load_crew_rosters.py               # Step 6: Synthetic crew roster loader
│   ├── load_all_data.py                   # Step 6: Master loader in dependency order
│   └── verify_database.py                 # Step 7: 10 database verification queries
├── tests/
│   ├── test_airport_data.py               # Master airport and runway unit tests
│   ├── test_synthetic_data.py             # Generator and operational constraint tests
│   └── test_database_loaders.py           # Loader idempotency and integrity tests
└── README.md                              # This documentation
```

---

## 3. Environment & Python Dependencies

The pipeline uses Python standard library modules (`sqlite3`, `csv`, `datetime`, `argparse`, `pathlib`, `random`, `unittest`) and `pandas` for master data cleaning.

```bash
# Recommended environment: Python 3.7+
pip install pandas
```

---

## 4. Pipeline Execution Workflow

### Step 1: Clean Master Airport & Runway Data
Filters raw OurAirports data against the agreed 10 target airports (`ATL`, `BOS`, `DEN`, `DFW`, `JFK`, `LAX`, `MIA`, `ORD`, `SEA`, `SFO`).

```bash
python scripts/clean_airports.py
```
*Output: Saves 10 cleaned airports to `data/processed/airports.csv` and 55 associated runways to `data/processed/runways.csv`.*

---

### Step 2: Generate Synthetic Operational Data
Generates 100 flights, 20 gates, 100 gate bookings, 80 staff, and 200 crew rosters using a deterministic random seed.

```bash
# Default execution (seed 20261026, 15-minute turnaround buffer)
python scripts/generate_synthetic_data.py

# Custom configuration example
python scripts/generate_synthetic_data.py --seed 42 --flights 150 --gates 30 --staff 100 --turnaround-buffer 20
```

Available CLI arguments:
- `--seed`: Integer random seed for reproducible generation (default: `20261026`).
- `--flights`: Number of synthetic flights (default: `100`).
- `--gates`: Total gates to generate across airports (default: `20`).
- `--gates-per-airport`: Number of gates per airport (overrides `--gates`).
- `--staff`: Number of staff records (default: `80`).
- `--bookings`: Number of gate bookings (default: `100`).
- `--crew-rosters`: Number of crew roster records (default: `200`).
- `--turnaround-buffer`: Buffer minutes between gate bookings (default: `15`).
- `--output-dir`: Output CSV directory (default: `data/synthetic`).

---

### Step 3: Validate Generated Datasets
Validates schema, types, primary/foreign keys, time ranges, and non-overlap constraints before database loading.

```bash
# Run all 43 schema, referential integrity, and operational consistency checks
python scripts/validate_synthetic_data.py

# Run validation including byte-for-byte reproducibility check
python scripts/validate_synthetic_data.py --check-reproducibility
```

---

### Step 4: Load Data into SQLite Database
Loads records in strict foreign-key dependency order. All loaders are **idempotent**: running them multiple times skips already existing records and avoids duplicate insertions.

```bash
# Optional dry-run: test lookups and mappings without writing to database
python scripts/load_all_data.py --dry-run

# Execute full load in dependency order into airport_operations.db
python scripts/load_all_data.py
```

Individual loader scripts can also be run independently:
```bash
python scripts/load_airports.py
python scripts/load_runways.py
python scripts/load_gates.py
python scripts/load_flights.py
python scripts/load_gate_bookings.py
python scripts/load_staff.py
python scripts/load_crew_rosters.py
```

---

### Step 5: Verify Database Integrity
Executes 10 automated SQL verification checks against the live database:

```bash
# Run database verification checks
python scripts/verify_database.py

# Run database verification including live idempotency verification
python scripts/verify_database.py --test-idempotency
```

Executed checks:
1. **Record counts**: Validates required record counts (`airports` >= 10, `runways` >= 55, `flights` >= 100, `gates` >= 20, `gate_bookings` >= 100, `staff` >= 80, `crew_rosters` >= 200).
2. **Synthetic flags**: Reports `is_synthetic = 1` vs `0` breakdown.
3. **Duplicate identifiers**: Verifies uniqueness of flight numbers, gate codes, staff names, and booking slots.
4. **Foreign-key referential integrity**: Executes `PRAGMA foreign_key_check` and explicit orphan detection joins.
5. **Mandatory fields**: Verifies no null or empty values in mandatory operational columns.
6. **Gate booking intervals**: Detects overlapping intervals on the same gate.
7. **Time range sanity**: Verifies `start_time < end_time` for all bookings.
8. **Crew assignment uniqueness**: Verifies no staff member is assigned to the same flight multiple times.
9. **Crew schedule conflicts**: Verifies no staff member is scheduled for overlapping duty periods across flights.
10. **Idempotency**: Verifies that re-running the loaders results in 0 additional insertions.

---

### Step 6: Run Automated Tests
All unit and integration tests are runnable with standard Python `unittest`:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Test coverage includes:
- `test_airport_data.py`: Validates master airport selection and runway mappings.
- `test_synthetic_data.py`: Tests deterministic generation, seed variation, CSV headers, unique IDs, foreign keys, gate non-overlap, crew non-overlap, error handling on missing input.
- `test_database_loaders.py`: Tests isolated database loading, dry-run mode, dependency order enforcement, idempotency, foreign key integrity, and error handling.

---

## 5. Schema Details & Business Key Mappings

The SQLite schema uses `PRAGMA foreign_keys = ON;`.

| Table | Business Key / Unique Identifier | Foreign Keys | Synthetic Flag |
| :--- | :--- | :--- | :--- |
| `airports` | `ident` (e.g. `KATL`), `iata_code` (`ATL`) | None | N/A (Master data) |
| `runways` | `(airport_id, runway_ident)` | `airport_id` -> `airports.id` | N/A (Master data) |
| `gates` | `(airport_id, gate_code)` (e.g. `G001`) | `airport_id` -> `airports.id` | `is_synthetic = 1` |
| `flights` | `flight_number` (e.g. `SN1943`) | `origin_airport_id`, `destination_airport_id` -> `airports.id` | `is_synthetic = 1` |
| `gate_bookings` | `(flight_id, gate_id, start_time)` | `flight_id` -> `flights.id`, `gate_id` -> `gates.id` | `is_synthetic = 1` |
| `staff` | `(airport_id, staff_name)` | `airport_id` -> `airports.id` | `is_synthetic = 1` |
| `crew_rosters` | `(flight_id, staff_id)` | `flight_id` -> `flights.id`, `staff_id` -> `staff.id` | `is_synthetic = 1` |

---

## 6. Known Assumptions and Limitations

1. **Airport Primary Keys**: In OurAirports raw CSVs, airport IDs are arbitrary integers (e.g., `3384` for ATL). In the SQLite database, `airports.id` is an internal autoincrement primary key (`1` to `10`). The loaders resolve the real database primary keys dynamically using `iata_code` or `ident`.
2. **Master Data vs Synthetic Data**: Master data (`airports` and `runways`) represents real world infrastructure and is stored without synthetic flags. All synthetic operational records (`flights`, `gates`, `gate_bookings`, `staff`, `crew_rosters`) have `is_synthetic = 1`.
3. **Turnaround Buffer**: The generator default turnaround buffer is 15 minutes. Adjacent bookings where one flight ends exactly when the next begins (`start_b == end_a`) are permitted when buffer is 0.
