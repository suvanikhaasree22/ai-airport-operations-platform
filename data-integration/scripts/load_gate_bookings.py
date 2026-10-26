import csv
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB_PROJECT=ROOT.parent/'airport-data-integration'
sys.path.insert(0,str(DB_PROJECT))
from database.db import get_connection
BOOKINGS_CSV=ROOT/'data'/'synthetic'/'gate_bookings.csv'; FLIGHTS_CSV=ROOT/'data'/'synthetic'/'flights.csv'
def load_bookings():
    with FLIGHTS_CSV.open(encoding='utf-8-sig',newline='') as f: flights={r['flight_id']:r['flight_number'] for r in csv.DictReader(f)}
    conn=get_connection()
    try:
        inserted=0
        with BOOKINGS_CSV.open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                gate=conn.execute('SELECT id FROM gates WHERE gate_code=?',(row['gate_id'].strip(),)).fetchone(); number=flights.get(row['flight_id']); flight=conn.execute('SELECT id FROM flights WHERE flight_number=?',(number,)).fetchone() if number else None
                if gate is None: raise ValueError('Gate not found: '+row['gate_id'])
                if flight is None: raise ValueError('Flight not found: '+row['flight_id'])
                overlap=conn.execute('SELECT 1 FROM gate_bookings WHERE gate_id=? AND start_time < ? AND ? < end_time LIMIT 1',(gate['id'],row['booking_end'],row['booking_start'])).fetchone()
                if overlap: raise ValueError('Overlapping booking for gate '+row['gate_id'])
                conn.execute('INSERT INTO gate_bookings (flight_id,gate_id,start_time,end_time,is_synthetic) VALUES (?,?,?,?,?)',(flight['id'],gate['id'],row['booking_start'],row['booking_end'],int(row['is_synthetic']))); inserted+=1
        conn.commit(); print('Gate bookings inserted:',inserted); print('Total bookings in database:',conn.execute('SELECT COUNT(*) FROM gate_bookings').fetchone()[0])
    except Exception: conn.rollback(); raise
    finally: conn.close()
if __name__=='__main__': load_bookings()
