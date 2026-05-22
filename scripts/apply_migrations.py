"""Apply Alembic migrations using the backend/alembic.ini config.

Run: python scripts/apply_migrations.py
"""
from alembic.config import Config
from alembic import command
import os
import sys

def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini_path = os.path.join(repo_root, 'backend', 'alembic.ini')
    if not os.path.exists(ini_path):
        print('alembic.ini not found at', ini_path)
        sys.exit(1)
    cfg = Config(ini_path)
    try:
        command.upgrade(cfg, 'head')
        print('Migrations applied')
    except Exception as exc:
        print('Migration failed:', exc)
        sys.exit(2)

if __name__ == '__main__':
    main()
