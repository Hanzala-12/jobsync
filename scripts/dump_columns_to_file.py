import sys, os
sys.path.insert(0, os.path.abspath('.'))
from backend.database import engine

from sqlalchemy import text

out = [f'engine url: {getattr(engine, "url", None)}']
conn = engine.connect()
for t in ('jobs','student_profiles'):
    out.append(f"Columns for {t}")
    res = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name=:t"), {'t': t}).fetchall()
    for r in res:
        out.append(f"{r[0]} {r[1]}")
conn.close()

with open('scripts/columns_out.txt','w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('written scripts/columns_out.txt')
