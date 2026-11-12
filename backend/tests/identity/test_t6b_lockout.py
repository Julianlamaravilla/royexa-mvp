"""T6b, T6-P3: five failed attempts in a row lock a user for fifteen minutes. Pure domain."""

from datetime import UTC, datetime, timedelta

from royexa.identity_access.domain import (
    LOCK_DURATION,
    MAX_FAILED_ATTEMPTS,
    Credential,
)

NOW = datetime(2026, 10, 30, 14, 0, tzinfo=UTC)


def _failures(count: int, start: Credential | None = None, at: datetime = NOW) -> Credential:
    credential = start or Credential("cobrador-1", "scrypt$16$8$1$AA$AA")
    for _ in range(count):
        credential = credential.after_failure(at)
    return credential


def test_t6b_the_policy_is_five_attempts_and_fifteen_minutes():
    assert (MAX_FAILED_ATTEMPTS, LOCK_DURATION) == (5, timedelta(minutes=15))


def test_t6b_four_failures_do_not_lock():
    credential = _failures(4)

    assert credential.failed_attempts == 4
    assert credential.is_locked(NOW) is False


def test_t6b_the_fifth_failure_locks_for_fifteen_minutes():
    credential = _failures(5)

    assert credential.is_locked(NOW) is True
    assert credential.locked_until == NOW + timedelta(minutes=15)
    assert credential.is_locked(NOW + timedelta(minutes=14, seconds=59)) is True
    assert credential.is_locked(NOW + timedelta(minutes=15)) is False


def test_t6b_a_success_clears_the_count_so_only_failures_in_a_row_count():
    credential = _failures(4).after_success()

    assert credential.failed_attempts == 0
    assert _failures(4, credential).is_locked(NOW) is False


def test_t6b_after_the_lock_expires_the_count_starts_again():
    locked = _failures(5)
    later = NOW + timedelta(minutes=16)

    after = locked.after_failure(later)

    assert after.failed_attempts == 1
    assert after.is_locked(later) is False
    assert _failures(4, after, later).is_locked(later) is True


def test_t6b_a_changed_password_clears_the_demo_mark_and_the_lock():
    locked = _failures(5)

    changed = locked.with_password("scrypt$16$8$1$BB$BB", NOW)

    assert (changed.is_demo, changed.failed_attempts, changed.locked_until) == (False, 0, None)
    assert changed.password_hash == "scrypt$16$8$1$BB$BB"
    assert changed.changed_at == NOW
