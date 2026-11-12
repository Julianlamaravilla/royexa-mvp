"""Closing a day's cash box (UC-07, RF-02, RN-02, CA-03, CA-04, T5-P1).

A module of its own: it needs the pending visits of `loans` and the box of `cash_box`, and
neither may depend on the other.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from typing import Protocol

from royexa.cash_box.desk import CashDesk
from royexa.cash_box.domain import (
    AdjustmentNotAllowed,
    CashClose,
    CashCloseNotAllowed,
    NoOpenCashBox,
    PendingVisitsRemain,
)
from royexa.cash_box.ports import CashCloseRepository, CashRepository
from royexa.identity_access.domain import Directory, User
from royexa.ledger.domain import LedgerEntry, LedgerEntryNotFound
from royexa.ledger.ports import LedgerRepository
from royexa.ledger.posting import LedgerPosting
from royexa.loans.application import VisitsUnitOfWork, pending_visits
from royexa.shared.calendar import BusinessCalendar
from royexa.shared.clock import Clock
from royexa.shared.money import Money


class ClosingUnitOfWork(VisitsUnitOfWork, Protocol):
    cash: CashRepository
    ledger: LedgerRepository
    cash_closes: CashCloseRepository


class CloseCashBox:
    def __init__(
        self,
        uow: Callable[[], ClosingUnitOfWork],
        clock: Clock,
        directory: Directory,
        calendar: BusinessCalendar,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._directory = directory
        self._calendar = calendar

    def execute(
        self, actor: User, collector_id: str, delivered: Money, device_time: datetime
    ) -> CashClose:
        if actor.id != collector_id:
            raise CashCloseNotAllowed(actor.id)
        now = self._clock.now()
        with self._uow() as uow:
            desk = CashDesk(uow.cash, self._directory, self._calendar)
            box = desk.box_of(collector_id, now)
            box.ensure_open()
            route = self._directory.route_of_collector(collector_id)
            pending = pending_visits(uow, self._calendar, route.id, box.day)
            if pending:
                raise PendingVisitsRemain(", ".join(item.client_id for item in pending))
            # T5-P1: the ledger, not the balance, says what the day collected in cash minus
            # what it disbursed; transfers and expired attempts carry no cash effect.
            expected = sum(
                (entry.cash_effect for entry in uow.ledger.for_cash_box(box.id)), Money(0)
            )
            close = CashClose.settle(box, actor, expected, delivered, device_time, now)
            box.close()
            desk.save(box)
            uow.cash_closes.add(close)
            uow.commit()
        return close


class RegisterAdjustment:
    """UC-08 (CA-08, T5-P4): the administrator corrects an entry with a new one. It lands in
    the box of the original's collector for the current day, so a closed day is corrected
    on the next one and the closed box and its close are left alone."""

    def __init__(
        self,
        uow: Callable[[], ClosingUnitOfWork],
        clock: Clock,
        directory: Directory,
        calendar: BusinessCalendar,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._directory = directory
        self._calendar = calendar

    def execute(
        self, actor: User, entry_id: str, amount: Money, reason: str, device_time: datetime
    ) -> LedgerEntry:
        if not actor.is_admin:
            raise AdjustmentNotAllowed(actor.id)
        now = self._clock.now()
        with self._uow() as uow:
            original = uow.ledger.get(entry_id)
            if original is None:
                raise LedgerEntryNotFound(entry_id)
            box = uow.cash.get(original.cash_box_id)
            if box is None:
                raise NoOpenCashBox(original.cash_box_id)
            desk = CashDesk(uow.cash, self._directory, self._calendar)
            entry = LedgerPosting(uow.ledger, desk).post_adjustment(
                original.id, box.collector_id, amount, reason, actor.id, device_time, now
            )
            uow.commit()
        return entry


class ClosesUnitOfWork(Protocol):
    cash_closes: CashCloseRepository

    def __enter__(self) -> ClosesUnitOfWork: ...
    def __exit__(self, *exc_info: object) -> None: ...


class CashCloseQueries:
    """What the administrator reads to see the discrepancies (CA-03)."""

    def __init__(self, uow: Callable[[], ClosesUnitOfWork]) -> None:
        self._uow = uow

    def all(self, collector_id: str | None = None, day: date | None = None) -> list[CashClose]:
        with self._uow() as uow:
            return uow.cash_closes.all(collector_id, day)
