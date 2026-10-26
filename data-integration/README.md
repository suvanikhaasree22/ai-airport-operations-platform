# Synthetic Airport Operations Data

This module generates reproducible synthetic records for airport operations and provides loader scripts intended to integrate with the team's SQLite airport-operations database.

## Generate CSVs

From the repository root:

```powershell
python data-integration/scripts/generate_synthetic_data.py
```

Output is written to `data-integration/data/synthetic/`. The generator uses a fixed seed by default and validates record counts, synthetic flags, references, and gate-booking overlaps.

## Load into the shared database

The loader scripts expect the team's database module at `airport-data-integration/database/db.py` and use its `get_connection()` function. Copy/merge this module into the shared integration repository before running the loaders; do not commit a populated SQLite database file or private/production records.

Suggested order:
1. `load_airports.py`
2. `load_gates.py`
3. `load_flights.py`
4. `load_gate_bookings.py`
5. `load_staff.py`
6. `load_crew_rosters.py`

Review the target schema before loading. The current agreed schema stores one `scheduled_time` for each flight, so the arrival-time field from the synthetic CSV is not currently persisted. The staff availability field is likewise only present in the CSV if the current schema does not provide a target column.

## Important

- All generated operational rows set `is_synthetic = 1`.
- Database IDs are resolved through airport IATA codes, flight numbers, and staff/gate mappings rather than assuming CSV IDs equal database primary keys.
- The loader does not write a database file to this repository.
