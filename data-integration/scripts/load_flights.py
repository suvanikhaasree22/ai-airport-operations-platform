import csv
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DB_PROJECT = ROOT.parent.parent / 'airport-data-integration'
sys.path.insert(0, str(DB_PROJECT.parent))
from airport_data_integration.database.db import get_connection
CSV_PATH = ROOT / 'data' / 'synthetic' / 'flights.csv'
def load_flights():
    with CSV_PATH.open(encoding='utf-8-sig',newline='') as f:
        conn=get_connection()
        try:
            inserted=0
            for row in csv.DictReader(f):
                origin=conn.execute('SELECT id FROM airports WHERE iata_code=?',(row['origin_code'].strip(),)).fetchone(); destination=conn.execute('SELECT id FROM airports WHERE iata_code=?',(row['destination_code'].strip(),)).fetchone()
                if origin is None or destination is None: raise ValueError('Airport reference missing for '+row['flight_number'])
                before=conn.total_changes
                conn.execute('INSERT OR IGNORE INTO flights (flight_number,origin_airport_id,destination_airport_id,scheduled_time,status,is_synthetic) VALUES (?,?,?,?,?,?)',(row['flight_number'].strip(),origin['id'],destination['id'],row['scheduled_departure'],row['status'].capitalize(),int(row['is_synthetic'])))
                inserted += conn.total_changes-before
            conn.commit(); print('Flight records inserted:',inserted); print('Total flights in database:',conn.execute('SELECT COUNT(*) FROM flights').fetchone()[0])
        except Exception: conn.rollback(); raise
        finally: conn.close()
if __name__ == '__main__': load_flights()
