"""Applies the SQL migrations as the owner role: python -m royexa.migrate

Every file is safe to repeat and all of them run on each start. A start-up ALTER TABLE can
lose a lock race against autovacuum and be chosen as the deadlock victim; nothing was
applied then, so it is simply tried again.
"""

import os
import time
from pathlib import Path

import psycopg
from psycopg import errors

MIGRATOR_URL = "postgresql://royexa_migrator:royexa_migrator@localhost:55432/royexa"
MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"
MAX_ATTEMPTS = 5
RETRY_PAUSE_SECONDS = 0.2


def _apply_once(target: str) -> list[str]:
    applied = []
    with psycopg.connect(target) as connection:
        for path in sorted(MIGRATIONS.glob("*.sql")):
            connection.execute(path.read_text())
            applied.append(path.name)
    return applied


def apply_migrations(url: str | None = None) -> list[str]:
    target = url or os.environ.get("ROYEXA_MIGRATOR_URL", MIGRATOR_URL)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return _apply_once(target)
        except errors.DeadlockDetected:
            if attempt == MAX_ATTEMPTS:
                raise
            time.sleep(RETRY_PAUSE_SECONDS * attempt)
    raise AssertionError("unreachable")


if __name__ == "__main__":
    print("\n".join(apply_migrations()))
