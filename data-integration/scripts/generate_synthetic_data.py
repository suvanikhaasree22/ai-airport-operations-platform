from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 20261026
AIRPORTS = [(3384, 'ATL'), (3422, 'BOS'), (3486, 'DEN'), (3488, 'DFW'), (3622, 'JFK'), (3632, 'LAX'), (3685, 'MIA'), (3754, 'ORD'), (3875, 'SEA'), (3903, 'SFO')]
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / 'data' / 'synthetic'

def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f'Wrote {len(rows):4d} records -> {path}')

def validate(output_dir: Path) -> None:
    def read(name):
        with (output_dir / name).open(encoding='utf-8', newline='') as f:
            return list(csv.DictReader(f))
    flights, gates = read('flights.csv'), read('gates.csv')
    bookings, staff, rosters = read('gate_bookings.csv'), read('staff.csv'), read('crew_rosters.csv')
    assert (len(flights), len(gates), len(bookings), len(staff), len(rosters)) == (100, 20, 100, 80, 200)
    flight_ids = {r['flight_id'] for r in flights}; gate_ids = {r['gate_id'] for r in gates}; staff_ids = {r['staff_id'] for r in staff}
    assert len({r['flight_number'] for r in flights}) == 100
    assert all(r['is_synthetic'] == '1' for dataset in (flights, gates, bookings, staff, rosters) for r in dataset)
    assert all(r['flight_id'] in flight_ids and r['gate_id'] in gate_ids for r in bookings)
    assert all(r['flight_id'] in flight_ids and r['staff_id'] in staff_ids for r in rosters)
    intervals = {}
    for row in bookings:
        start, end = datetime.fromisoformat(row['booking_start']), datetime.fromisoformat(row['booking_end'])
        assert start < end
        intervals.setdefault(row['gate_id'], []).append((start, end))
    for values in intervals.values():
        values.sort()
        assert all(a[1] <= b[0] for a, b in zip(values, values[1:])), 'overlapping gate bookings'
    print('PASS: counts, references, flags, and gate booking overlaps validated.')

def generate(output_dir: Path = DEFAULT_OUTPUT, seed: int = SEED) -> None:
    rng = random.Random(seed)
    airport_codes = [code for _, code in AIRPORTS]
    airport_id = dict((code, ident) for ident, code in AIRPORTS)
    flights = []
    base = datetime(2026, 11, 1, 5, 0)
    for i in range(1, 101):
        origin = rng.choice(airport_codes); destination = rng.choice([x for x in airport_codes if x != origin])
        departure = base + timedelta(days=rng.randrange(7), minutes=15 * rng.randrange(48))
        arrival = departure + timedelta(minutes=rng.randrange(70, 361))
        flights.append({'flight_id': f'F{i:04d}', 'flight_number': f'SN{1000+i:04d}', 'origin_airport_id': airport_id[origin], 'origin_code': origin, 'destination_airport_id': airport_id[destination], 'destination_code': destination, 'scheduled_departure': departure.strftime('%Y-%m-%dT%H:%M'), 'scheduled_arrival': arrival.strftime('%Y-%m-%dT%H:%M'), 'status': rng.choice(['scheduled', 'scheduled', 'delayed']), 'is_synthetic': 1})
    gates = []
    for i in range(1, 21):
        aid, code = AIRPORTS[(i-1) % len(AIRPORTS)]
        gates.append({'gate_id': f'G{i:03d}', 'airport_id': aid, 'airport_code': code, 'terminal': rng.choice(['A','B','C','D']), 'gate_status': rng.choice(['available','available','maintenance']), 'is_synthetic': 1})
    bookings = []; bid = 1
    for gate in gates:
        for day in range(5):
            start = datetime(2026, 11, 1, 6, 0) + timedelta(days=day, hours=gate['gate_id'].__hash__() % 4)
            flight = flights[(bid * 7) % len(flights)]
            bookings.append({'booking_id': f'B{bid:04d}', 'gate_id': gate['gate_id'], 'flight_id': flight['flight_id'], 'booking_start': start.strftime('%Y-%m-%dT%H:%M'), 'booking_end': (start+timedelta(minutes=75)).strftime('%Y-%m-%dT%H:%M'), 'is_synthetic': 1})
            bid += 1
    # Reproducibility excludes Python's randomized hash: set the schedule by gate number.
    for row in bookings:
        gate_no = int(row['gate_id'][1:])
        slot = int(row['booking_id'][1:]) - 1
        day = slot // 20
        start = datetime(2026, 11, 1, 6, 0) + timedelta(days=day, hours=(gate_no - 1) % 4)
        row['booking_start'] = start.strftime('%Y-%m-%dT%H:%M')
        row['booking_end'] = (start + timedelta(minutes=75)).strftime('%Y-%m-%dT%H:%M')
    staff = [{'staff_id': f'S{i:04d}', 'staff_name': f'Synthetic Staff {i:03d}', 'role': rng.choice(['ground_staff','gate_agent','baggage_staff','operations']), 'home_airport_code': airport_codes[(i-1)%len(airport_codes)], 'availability_status': rng.choice(['available','assigned','off_duty']), 'is_synthetic': 1} for i in range(1,81)]
    rosters = []
    for i in range(1,201):
        flight = flights[(i-1)%100]; person = staff[(i-1)%80]
        start = datetime.strptime(flight['scheduled_departure'], '%Y-%m-%dT%H:%M') - timedelta(hours=2)
        rosters.append({'roster_id': f'R{i:04d}', 'flight_id': flight['flight_id'], 'staff_id': person['staff_id'], 'duty_start': start.strftime('%Y-%m-%dT%H:%M'), 'duty_end': (start+timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M'), 'is_synthetic': 1})
    write_csv(output_dir/'flights.csv', ['flight_id','flight_number','origin_airport_id','origin_code','destination_airport_id','destination_code','scheduled_departure','scheduled_arrival','status','is_synthetic'], flights)
    write_csv(output_dir/'gates.csv', ['gate_id','airport_id','airport_code','terminal','gate_status','is_synthetic'], gates)
    write_csv(output_dir/'gate_bookings.csv', ['booking_id','gate_id','flight_id','booking_start','booking_end','is_synthetic'], bookings)
    write_csv(output_dir/'staff.csv', ['staff_id','staff_name','role','home_airport_code','availability_status','is_synthetic'], staff)
    write_csv(output_dir/'crew_rosters.csv', ['roster_id','flight_id','staff_id','duty_start','duty_end','is_synthetic'], rosters)
    validate(output_dir)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--seed', type=int, default=SEED)
    args = parser.parse_args()
    generate(args.output_dir, args.seed)
