"""In-memory persistence with snapshot transactions.

Each unit of work reads a private copy. `commit` publishes only what it changed and
refuses a stale write, so concurrent use behaves like the database would: nothing leaks
before commit, a rollback leaves no trace, and the loser of a race learns about it.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from threading import Lock
from typing import Protocol, Self

from royexa.cash_box.domain import CashBox, CashClose
from royexa.clients.domain import Client
from royexa.ledger.domain import DuplicateLedgerEntry, LedgerEntry
from royexa.ledger.ports import LedgerRepository
from royexa.loans.domain import Loan, NonPayment, Payment, RenewalException
from royexa.sales.domain import Disbursement
from royexa.shared.errors import StaleWrite
from royexa.shared.outbox import NoticeStatus, OutboxMessage

_KEYED_TABLES = (
    "clients",
    "disbursements",
    "loans",
    "payments",
    "non_payments",
    "renewal_exceptions",
    "cash_boxes",
    "cash_closes",
    "outbox",
)


@dataclass
class Tables:
    clients: dict[str, Client] = field(default_factory=dict)
    disbursements: dict[str, Disbursement] = field(default_factory=dict)
    loans: dict[str, Loan] = field(default_factory=dict)
    payments: dict[str, Payment] = field(default_factory=dict)
    non_payments: dict[str, NonPayment] = field(default_factory=dict)
    renewal_exceptions: dict[str, RenewalException] = field(default_factory=dict)
    cash_boxes: dict[str, CashBox] = field(default_factory=dict)
    cash_closes: dict[str, CashClose] = field(default_factory=dict)
    outbox: dict[str, OutboxMessage] = field(default_factory=dict)
    ledger: list[LedgerEntry] = field(default_factory=list)


class InMemoryStore:
    def __init__(self, tables: Tables | None = None) -> None:
        self.tables = tables or Tables()
        self.lock = Lock()


def _ensure_unique(entries: list[LedgerEntry], entry: LedgerEntry) -> None:
    """Same contract as the database constraint (INV-02, ADR-004)."""
    for existing in entries:
        if (existing.operation_id, existing.entry_type) == (entry.operation_id, entry.entry_type):
            raise DuplicateLedgerEntry(entry.operation_id)


class InMemoryLedgerRepository:
    def __init__(self, entries: list[LedgerEntry]) -> None:
        self._entries = entries

    def append(self, entry: LedgerEntry) -> None:
        _ensure_unique(self._entries, entry)
        self._entries.append(entry)

    def for_disbursement(self, disbursement_id: str) -> list[LedgerEntry]:
        return [entry for entry in self._entries if entry.disbursement_id == disbursement_id]

    def for_cash_box(self, cash_box_id: str) -> list[LedgerEntry]:
        return [entry for entry in self._entries if entry.cash_box_id == cash_box_id]

    def all(self) -> list[LedgerEntry]:
        return list(self._entries)


class InMemoryClientRepository:
    def __init__(self, tables: Tables) -> None:
        self._rows = tables.clients

    def add(self, client: Client) -> None:
        self._rows[client.id] = client

    def get(self, client_id: str) -> Client | None:
        return self._rows.get(client_id)

    def all(self) -> list[Client]:
        return list(self._rows.values())


class InMemoryDisbursementRepository:
    def __init__(self, tables: Tables) -> None:
        self._rows = tables.disbursements

    def add(self, disbursement: Disbursement) -> None:
        self._rows[disbursement.id] = disbursement

    def get(self, disbursement_id: str) -> Disbursement | None:
        return self._rows.get(disbursement_id)

    def save(self, disbursement: Disbursement) -> None:
        self._rows[disbursement.id] = disbursement


class InMemoryLoanRepository:
    def __init__(self, tables: Tables) -> None:
        self._loans = tables.loans
        self._exceptions = tables.renewal_exceptions

    def add(self, loan: Loan) -> None:
        self._loans[loan.id] = loan

    def save(self, loan: Loan) -> None:
        self._loans[loan.id] = loan

    def get(self, loan_id: str) -> Loan | None:
        return self._loans.get(loan_id)

    def unsettled_for_client(self, client_id: str) -> Loan | None:
        for loan in self._loans.values():
            if loan.client_id == client_id and not loan.is_settled:
                return loan
        return None

    def for_client(self, client_id: str) -> list[Loan]:
        return [loan for loan in self._loans.values() if loan.client_id == client_id]

    def add_exception(self, exception: RenewalException) -> None:
        self._exceptions[exception.id] = exception

    def save_exception(self, exception: RenewalException) -> None:
        self._exceptions[exception.id] = exception

    def get_exception(self, exception_id: str) -> RenewalException | None:
        return self._exceptions.get(exception_id)

    def open_exception_for(self, client_id: str) -> RenewalException | None:
        for exception in self._exceptions.values():
            if exception.client_id == client_id and exception.consumed_by is None:
                return exception
        return None


class InMemoryPaymentRepository:
    def __init__(self, tables: Tables) -> None:
        self._rows = tables.payments

    def add(self, payment: Payment) -> None:
        self._rows[payment.id] = payment

    def for_loan(self, loan_id: str) -> list[Payment]:
        return [payment for payment in self._rows.values() if payment.loan_id == loan_id]


class InMemoryNonPaymentRepository:
    def __init__(self, tables: Tables) -> None:
        self._rows = tables.non_payments

    def add(self, non_payment: NonPayment) -> None:
        self._rows[non_payment.id] = non_payment

    def for_loan(self, loan_id: str) -> list[NonPayment]:
        return [item for item in self._rows.values() if item.loan_id == loan_id]


class InMemoryCashRepository:
    def __init__(self, tables: Tables) -> None:
        self._boxes = tables.cash_boxes

    def box_of_day(self, collector_id: str, day: date) -> CashBox | None:
        for box in self._boxes.values():
            if box.collector_id == collector_id and box.day == day:
                return box
        return None

    def save(self, box: CashBox) -> None:
        self._boxes[box.id] = box


class InMemoryCashCloseRepository:
    def __init__(self, tables: Tables) -> None:
        self._rows = tables.cash_closes

    def add(self, close: CashClose) -> None:
        if any(item.cash_box_id == close.cash_box_id for item in self._rows.values()):
            raise StaleWrite(f"cash_close/{close.cash_box_id}")
        self._rows[close.id] = close

    def all(self, collector_id: str | None = None, day: date | None = None) -> list[CashClose]:
        return [
            item
            for item in self._rows.values()
            if (collector_id is None or item.collector_id == collector_id)
            and (day is None or item.day == day)
        ]


class InMemoryOutbox:
    def __init__(self, tables: Tables) -> None:
        self._messages = tables.outbox

    def add(self, message: OutboxMessage) -> None:
        self._messages[message.id] = message

    def get(self, message_id: str) -> OutboxMessage | None:
        return self._messages.get(message_id)

    def save(self, message: OutboxMessage) -> None:
        self._messages[message.id] = message

    def pending(self) -> list[OutboxMessage]:
        return [m for m in self._messages.values() if m.status is NoticeStatus.PENDING]

    def all(
        self, disbursement_id: str | None = None, payment_id: str | None = None
    ) -> list[OutboxMessage]:
        return [
            m
            for m in self._messages.values()
            if (disbursement_id is None or m.disbursement_id == disbursement_id)
            and (payment_id is None or m.payment_id == payment_id)
        ]


class LedgerSession(Protocol):
    """A ledger living in its own transaction, committed with the unit of work."""

    repository: LedgerRepository

    def commit(self) -> None: ...
    def rollback(self) -> None: ...


class InMemoryUnitOfWork:
    def __init__(self, store: InMemoryStore, ledger_session=None) -> None:
        self._store = store
        self._ledger_session_factory = ledger_session
        self._session: LedgerSession | None = None
        self._committed = False

    def __enter__(self) -> Self:
        self._committed = False
        with self._store.lock:
            self._base = deepcopy(self._store.tables)
        self._work = deepcopy(self._base)
        if self._ledger_session_factory is None:
            self.ledger = InMemoryLedgerRepository(self._work.ledger)
            self.clients = InMemoryClientRepository(self._work)
            self.disbursements = InMemoryDisbursementRepository(self._work)
            self.loans = InMemoryLoanRepository(self._work)
            self.payments = InMemoryPaymentRepository(self._work)
            self.non_payments = InMemoryNonPaymentRepository(self._work)
            self.cash_closes = InMemoryCashCloseRepository(self._work)
            self.cash = InMemoryCashRepository(self._work)
            self.outbox = InMemoryOutbox(self._work)
        else:
            self._session = self._ledger_session_factory()
            self.ledger = self._session.repository
            # T1a, T1b, T2a: a session that carries the state replaces the in-memory copies.
            self.clients = getattr(self._session, "clients", None) or InMemoryClientRepository(
                self._work
            )
            self.disbursements = getattr(
                self._session, "disbursements", None
            ) or InMemoryDisbursementRepository(self._work)
            self.loans = getattr(self._session, "loans", None) or InMemoryLoanRepository(self._work)
            self.cash = getattr(self._session, "cash", None) or InMemoryCashRepository(self._work)
            self.outbox = getattr(self._session, "outbox", None) or InMemoryOutbox(self._work)
            self.payments = getattr(self._session, "payments", None) or InMemoryPaymentRepository(
                self._work
            )
            self.non_payments = getattr(
                self._session, "non_payments", None
            ) or InMemoryNonPaymentRepository(self._work)
            self.cash_closes = getattr(
                self._session, "cash_closes", None
            ) or InMemoryCashCloseRepository(self._work)
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._session is not None and not self._committed:
            self._session.rollback()

    def commit(self) -> None:
        with self._store.lock:
            committed = self._store.tables
            new_entries = self._work.ledger[len(self._base.ledger) :]
            for entry in new_entries:
                _ensure_unique(committed.ledger, entry)
            changes = self._changes()
            for table, key, _ in changes:
                if getattr(committed, table).get(key) != getattr(self._base, table).get(key):
                    raise StaleWrite(f"{table}/{key}")
            if self._session is not None:
                self._session.commit()
            for table, key, value in changes:
                getattr(committed, table)[key] = value
            committed.ledger.extend(new_entries)
        self._committed = True

    def _changes(self) -> list[tuple[str, str, object]]:
        return [
            (table, key, value)
            for table in _KEYED_TABLES
            for key, value in getattr(self._work, table).items()
            if getattr(self._base, table).get(key) != value
        ]
