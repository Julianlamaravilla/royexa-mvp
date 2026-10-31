"""Applies the SQL migrations as the owner role: python -m royexa.migrate"""

import os
from pathlib import Path

import psycopg

MIGRATOR_URL = "postgresql://royexa_migrator:royexa_migrator@localhost:55432/royexa"
MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


def apply_migrations(url: str | None = None) -> list[str]:
    target = url or os.environ.get("ROYEXA_MIGRATOR_URL", MIGRATOR_URL)
    applied = []
    with psycopg.connect(target) as connection:
        for path in sorted(MIGRATIONS.glob("*.sql")):
            connection.execute(path.read_text())
            applied.append(path.name)
    return applied


if __name__ == "__main__":
    print("\n".join(apply_migrations()))
