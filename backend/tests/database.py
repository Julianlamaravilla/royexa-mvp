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


def reset_database() -> None:
    """Empty every table as the owner, which the application role cannot do (ADR-001)."""
    apply_migrations()
    with psycopg.connect(MIGRATOR_URL) as owner:
        owner.execute(f"TRUNCATE {', '.join(_TABLES)}")
