import sys, os
sys.path.insert(0, os.path.abspath('.'))
from backend.database import engine
from sqlalchemy import text

def main():
    conn = engine.connect()
    for t in ('jobs','student_profiles'):
        print('\nColumns for', t)
        res = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name=:t"), {'t': t}).fetchall()
        for r in res:
            print(r[0], r[1])
    conn.close()

if __name__ == '__main__':
    main()
