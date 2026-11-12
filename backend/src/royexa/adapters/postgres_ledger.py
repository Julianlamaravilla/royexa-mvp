"""Ledger on PostgreSQL under the application role (ADR-001, EV-01, EV-02).

Same LedgerRepository port as the in-memory adapter. Immutability lives in the role's
privileges, which is what an in-memory ledger cannot prove (ALT-01A).
"""

from __future__ import annotations

import psycopg
from psycopg import errors

from royexa.ledger.domain import DuplicateLedgerEntry, LedgerEntry, LedgerEntryType
from royexa.shared.money import Money

_COLUMNS = (
    "id, disbursement_id, entry_type, amount_cents, cash_box_id, "
    "actor_id, device_time, server_time, reason, payment_id, payment_method"
)


def _entry(row: tuple) -> LedgerEntry:
    return LedgerEntry(
        row[0], row[1], LedgerEntryType(row[2]), Money(row[3]), *row[4:]
    )


class PostgresLedgerRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def append(self, entry: LedgerEntry) -> None:
        try:
            self._connection.execute(
                f"INSERT INTO ledger_entry ({_COLUMNS}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    entry.id,
                    entry.disbursement_id,
                    entry.entry_type.value,
                    entry.amount.cents,
                    entry.cash_box_id,
                    entry.actor_id,
                    entry.device_time,
                    entry.server_time,
                    entry.reason,
                    entry.payment_id,
                    entry.payment_method,
                ),
            )
        except errors.UniqueViolation as error:
            raise DuplicateLedgerEntry(entry.operation_id) from error

    def for_disbursement(self, disbursement_id: str) -> list[LedgerEntry]:
        rows = self._connection.execute(
            f"SELECT {_COLUMNS} FROM ledger_entry WHERE disbursement_id = %s "
            "ORDER BY server_time, id",
            (disbursement_id,),
        )
        return [_entry(row) for row in rows]

    def for_cash_box(self, cash_box_id: str) -> list[LedgerEntry]:
        rows = self._connection.execute(
            f"SELECT {_COLUMNS} FROM ledger_entry WHERE cash_box_id = %s ORDER BY server_time, id",
            (cash_box_id,),
        )
        return [_entry(row) for row in rows]

    def all(self) -> list[LedgerEntry]:
        rows = self._connection.execute(
            f"SELECT {_COLUMNS} FROM ledger_entry ORDER BY server_time, id"
        )
        return [_entry(row) for row in rows]


class PostgresLedgerSession:
    """One transaction per unit of work. Whatever ends it closes the connection, even when
    that step fails. Only `rollback` tolerates a finished session: the unit of work calls it
    on the way out, and raising there would hide the error that got it there."""

    def __init__(self, url: str) -> None:
        self._connection = psycopg.connect(url)
        # Like the in-memory snapshot: each unit of work reads a private, consistent copy,
        # so the loser of a race never sees half of the winner's commit (ADR-004).
        self._connection.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        self.repository = PostgresLedgerRepository(self._connection)

    def commit(self) -> None:
        try:
            self._connection.commit()
        finally:
            self._connection.close()

    def rollback(self) -> None:
        if self._connection.closed:
            return
        try:
            self._connection.rollback()
        finally:
            self._connection.close()
