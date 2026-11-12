"""A deadlock while migrating is retried: autovacuum can win a lock race against an ALTER
TABLE at start-up, and every migration is safe to repeat."""

import pytest
from psycopg import errors

from royexa import migrate


def _flaky(failures: int, calls: list):
    def apply_once(target: str) -> list[str]:
        calls.append(target)
        if len(calls) <= failures:
            raise errors.DeadlockDetected("deadlock detected")
        return ["001_ledger.sql"]

    return apply_once


def test_a_deadlock_is_retried_until_the_migrations_apply(monkeypatch):
    calls: list = []
    monkeypatch.setattr(migrate, "_apply_once", _flaky(2, calls))
    monkeypatch.setattr(migrate.time, "sleep", lambda _: None)

    assert migrate.apply_migrations("postgresql://x") == ["001_ledger.sql"]
    assert len(calls) == 3


def test_a_persistent_deadlock_surfaces_after_the_last_attempt(monkeypatch):
    calls: list = []
    monkeypatch.setattr(migrate, "_apply_once", _flaky(99, calls))
    monkeypatch.setattr(migrate.time, "sleep", lambda _: None)

    with pytest.raises(errors.DeadlockDetected):
        migrate.apply_migrations("postgresql://x")

    assert len(calls) == migrate.MAX_ATTEMPTS


def test_any_other_error_is_not_retried(monkeypatch):
    calls: list = []

    def broken(target: str) -> list[str]:
        calls.append(target)
        raise errors.SyntaxError("bad migration")

    monkeypatch.setattr(migrate, "_apply_once", broken)

    with pytest.raises(errors.SyntaxError):
        migrate.apply_migrations("postgresql://x")

    assert len(calls) == 1
