import sys, os
sys.path.insert(0, os.path.abspath('.'))
from backend.database import engine
from sqlalchemy import text

def cols(table):
    conn=engine.connect()
    res=conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name=:t"), {'t':table}).fetchall()
    conn.close()
    return [r[0] for r in res]

def main():
    print('engine', getattr(engine,'url',None))
    print('jobs before:', cols('jobs'))
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN job_skills JSON DEFAULT '[]'::jsonb"))
        print('alter executed (committed)')
    except Exception as e:
        print('alter failed', e)
    print('jobs after:', cols('jobs'))
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE student_profiles ADD COLUMN profile_skills JSON DEFAULT '[]'::jsonb"))
        print('profile alter executed (committed)')
    except Exception as e:
        print('profile alter failed', e)

    print('student_profiles after:', cols('student_profiles'))

if __name__ == '__main__':
    main()
