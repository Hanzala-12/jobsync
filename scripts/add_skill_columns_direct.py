"""Add skill JSON columns to existing tables if they are missing.

This attempts ALTER TABLE statements; if the DB is SQLite and doesn't support JSON/IF NOT EXISTS,
the script will attempt to add a TEXT column as a fallback.
"""
import sys
import os
from sqlalchemy import create_engine, text

# ensure repo root is on path so 'backend' imports work
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.database import engine

def add_columns():
    conn = engine.connect()
    dialect = engine.dialect.name
    stmts = []
    if dialect in ("postgresql", "postgres"):
        stmts = [
            "ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS profile_skills JSON DEFAULT '[]'::jsonb",
            "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_skills JSON DEFAULT '[]'::jsonb",
        ]
    else:
        # SQLite and others: add as TEXT defaulting to '[]' if JSON unsupported
        stmts = [
            "ALTER TABLE student_profiles ADD COLUMN profile_skills TEXT DEFAULT '[]'",
            "ALTER TABLE jobs ADD COLUMN job_skills TEXT DEFAULT '[]'",
        ]

    for s in stmts:
        try:
            conn.execute(text(s))
            print('Executed:', s)
        except Exception as exc:
            print('Skipping/failed:', s, exc)

    conn.close()

if __name__ == '__main__':
    add_columns()
