import csv
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DB_PROJECT = ROOT.parent / 'airport-data-integration'
sys.path.insert(0, str(DB_PROJECT))
from database.db import get_connection
CSV_PATH = ROOT / 'data' / 'synthetic' / 'gates.csv'
def load_gates():
    with CSV_PATH.open(encoding='utf-8-sig', newline='') as f:
        conn = get_connection()
        try:
            inserted = 0
            for row in csv.DictReader(f):
                airport = conn.execute('SELECT id FROM airports WHERE iata_code=?',(row['airport_code'].strip(),)).fetchone()
                if airport is None: raise ValueError('Airport not found: '+row['airport_code'])
                before=conn.total_changes
                conn.execute('INSERT OR IGNORE INTO gates (airport_id,gate_code,is_synthetic) VALUES (?,?,?)',(airport['id'],row['gate_id'].strip(),int(row['is_synthetic'])))
                inserted += conn.total_changes-before
            conn.commit(); print('Gate records inserted:',inserted); print('Total gates in database:',conn.execute('SELECT COUNT(*) FROM gates').fetchone()[0])
        except Exception: conn.rollback(); raise
        finally: conn.close()
if __name__ == '__main__': load_gates()
