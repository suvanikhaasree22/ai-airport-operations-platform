import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PROJECT = ROOT.parent / 'airport-data-integration'
sys.path.insert(0, str(DB_PROJECT))
from database.db import get_connection

CSV_PATH = ROOT / 'data' / 'processed' / 'airports.csv'

def load_airports():
    with CSV_PATH.open(encoding='utf-8-sig', newline='') as f:
        conn = get_connection()
        try:
            inserted = 0
            for row in csv.DictReader(f):
                code, name = row.get('iata_code','').strip(), row.get('name','').strip()
                if not code or not name: continue
                before = conn.total_changes
                conn.execute('''INSERT OR IGNORE INTO airports (ident,name,iata_code,icao_code,latitude,longitude,country) VALUES (?,?,?,?,?,?,?)''', (row.get('ident','').strip() or None, name, code, row.get('icao_code','').strip() or None, float(row['latitude_deg']) if row.get('latitude_deg') else None, float(row['longitude_deg']) if row.get('longitude_deg') else None, row.get('iso_country','').strip() or None))
                inserted += conn.total_changes-before
            conn.commit()
            print('Airport records inserted:', inserted)
            print('Total airports in database:', conn.execute('SELECT COUNT(*) FROM airports').fetchone()[0])
        except Exception: conn.rollback(); raise
        finally: conn.close()

if __name__ == '__main__': load_airports()
