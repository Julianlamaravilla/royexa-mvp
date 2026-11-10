"""Owner-role helper for tests that share one PostgreSQL database."""

import psycopg

from royexa.migrate import MIGRATOR_URL, apply_migrations

_TABLES = (
    "ledger_entry",
    "outbox_message",
    "renewal_exception",
    "loan_installment",
    "loan",
    "cash_box",
)


def reset_database() -> None:
    """Empty every table as the owner, which the application role cannot do (ADR-001)."""
    apply_migrations()
    with psycopg.connect(MIGRATOR_URL) as owner:
        owner.execute(f"TRUNCATE {', '.join(_TABLES)}")
