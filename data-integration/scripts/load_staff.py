import csv
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DB_PROJECT=ROOT.parent.parent/'airport-data-integration'; sys.path.insert(0,str(DB_PROJECT.parent))
from airport_data_integration.database.db import get_connection
CSV_PATH=ROOT/'data'/'synthetic'/'staff.csv'
def load_staff():
    with CSV_PATH.open(encoding='utf-8-sig',newline='') as f:
        conn=get_connection()
        try:
            inserted=0
            for row in csv.DictReader(f):
                airport=conn.execute('SELECT id FROM airports WHERE iata_code=?',(row['home_airport_code'].strip(),)).fetchone()
                if airport is None: raise ValueError('Airport not found: '+row['home_airport_code'])
                conn.execute('INSERT INTO staff (airport_id,staff_name,role,is_synthetic) VALUES (?,?,?,?)',(airport['id'],row['staff_name'].strip(),row['role'].strip(),int(row['is_synthetic']))); inserted+=1
            conn.commit(); print('Staff records inserted:',inserted); print('Total staff in database:',conn.execute('SELECT COUNT(*) FROM staff').fetchone()[0])
        except Exception: conn.rollback(); raise
        finally: conn.close()
if __name__=='__main__': load_staff()
