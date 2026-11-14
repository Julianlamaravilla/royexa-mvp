"""Closing a day's cash box (UC-07, RF-02, RN-02, CA-03, CA-04, T5-P1).

A module of its own: it needs the pending visits of `loans` and the box of `cash_box`, and
neither may depend on the other.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Protocol

from royexa.cash_box.desk import CashDesk
from royexa.cash_box.domain import (
    AdjustmentNotAllowed,
    CashClose,
    CashBox,
    CashCloseNotAllowed,
    InvalidPeriod,
    NoOpenCashBox,
    PendingVisitsRemain,
)
from royexa.cash_box.ports import CashCloseRepository, CashRepository
from royexa.identity_access.domain import Directory, User
from royexa.ledger.domain import LedgerEntry, LedgerEntryNotFound, LedgerEntryType
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
    cash: CashRepository
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


MAX_PERIOD_DAYS = 366


@dataclass(frozen=True)
class DayEvolution:
    day: date
    count: int
    net: Money


@dataclass(frozen=True)
class DiscrepancyReport:
    since: date
    until: date
    items: list[CashClose]
    shortage: Money
    surplus: Money
    days: list[DayEvolution]
    unclosed: list[CashBox]

    @property
    def count(self) -> int:
        return len(self.items)


def resolve_period(today: date, since: date | None, until: date | None) -> tuple[date, date]:
    """T9-P1: the month up to today when no dates are given; an inverted or over-long period
    is refused."""
    since = since or today.replace(day=1)
    until = until or today
    if since > until:
        raise InvalidPeriod("the period starts after it ends")
    if (until - since).days >= MAX_PERIOD_DAYS:
        raise InvalidPeriod(f"the period spans more than {MAX_PERIOD_DAYS} days")
    return since, until


class DiscrepancyQueries:
    """UC-09 (RF-07, CA-13, T9-P1 to T9-P3): the closes of a period with a difference, their
    evolution by collection day, and the boxes of past days that were never closed."""

    def __init__(
        self, uow: Callable[[], ClosesUnitOfWork], clock: Clock, calendar: BusinessCalendar
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._calendar = calendar

    def report(self, since: date | None = None, until: date | None = None) -> DiscrepancyReport:
        today = self._calendar.day_of(self._clock.now())
        since, until = resolve_period(today, since, until)
        with self._uow() as uow:
            closes = [c for c in uow.cash_closes.all() if since <= c.day <= until]
            # Today's box is still being worked; only past days can have been left open.
            unclosed = uow.cash.open_between(since, min(until, today - timedelta(days=1)))
        items = [close for close in closes if close.discrepancy.cents != 0]
        gaps = [item.discrepancy.cents for item in items]
        days = [
            DayEvolution(
                day,
                sum(1 for item in items if item.day == day),
                Money(sum(item.discrepancy.cents for item in items if item.day == day)),
            )
            for day in (since + timedelta(days=n) for n in range((until - since).days + 1))
            if self._calendar.is_collection_day(day)
        ]
        return DiscrepancyReport(
            since,
            until,
            items,
            Money(-sum(gap for gap in gaps if gap < 0)),
            Money(sum(gap for gap in gaps if gap > 0)),
            days,
            unclosed,
        )


@dataclass(frozen=True)
class DayFlow:
    day: date
    collected: Money
    disbursed: Money


@dataclass(frozen=True)
class FlowReport:
    since: date
    until: date
    days: list[DayFlow]
    collected: Money
    disbursed: Money


class CashFlowQueries:
    """T14b: per collection day, what was collected (every payment, cash or transfer) against
    what was disbursed (confirmed disbursements). Adjustments and expired attempts move no
    money of either kind, so they are left out. The period is the one of the discrepancies."""

    def __init__(
        self, uow: Callable[[], ClosingUnitOfWork], clock: Clock, calendar: BusinessCalendar
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._calendar = calendar

    def report(self, since: date | None = None, until: date | None = None) -> FlowReport:
        today = self._calendar.day_of(self._clock.now())
        since, until = resolve_period(today, since, until)
        collected: dict[date, int] = {}
        disbursed: dict[date, int] = {}
        with self._uow() as uow:
            entries = uow.ledger.all()
        for entry in entries:
            day = self._calendar.day_of(entry.server_time)
            if entry.entry_type is LedgerEntryType.PAYMENT:
                collected[day] = collected.get(day, 0) + entry.amount.cents
            elif entry.entry_type is LedgerEntryType.DISBURSEMENT:
                disbursed[day] = disbursed.get(day, 0) + entry.amount.cents
        days = [
            DayFlow(day, Money(collected.get(day, 0)), Money(disbursed.get(day, 0)))
            for day in (since + timedelta(days=n) for n in range((until - since).days + 1))
            if self._calendar.is_collection_day(day)
        ]
        return FlowReport(
            since,
            until,
            days,
            Money(sum(d.collected.cents for d in days)),
            Money(sum(d.disbursed.cents for d in days)),
        )
