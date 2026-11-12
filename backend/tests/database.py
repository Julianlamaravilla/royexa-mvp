"""Owner-role helper for tests that share one PostgreSQL database."""

import psycopg

from royexa.migrate import MIGRATOR_URL, apply_migrations

_TABLES = (
    "ledger_entry",
    "refused_approval_attempt",
    "disbursement",
    "outbox_message",
    "renewal_exception",
    "non_payment",
    "payment_allocation",
    "payment",
    "loan_installment",
    "loan",
    "cash_close",
    "cash_box",
    "client",
)


_migrated = False


def reset_database() -> None:
    """Empty every table as the owner, which the application role cannot do (ADR-001).
    The schema is applied once per test run: re-running every ALTER TABLE before each of
    hundreds of tests only multiplies the chances of a lock race with autovacuum."""
    global _migrated
    if not _migrated:
        apply_migrations()
        _migrated = True
    with psycopg.connect(MIGRATOR_URL) as owner:
        owner.execute(f"TRUNCATE {', '.join(_TABLES)}")
