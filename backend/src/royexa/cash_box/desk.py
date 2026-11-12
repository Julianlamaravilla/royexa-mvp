"""The cash desk: finds the box of a collector's day and opens it on the first movement
(T5-P2). Business code asks the desk, never the repository, for the box of a movement."""

from __future__ import annotations

from datetime import date, datetime

from royexa.cash_box.domain import CashBox, NoOpenCashBox
from royexa.cash_box.ports import CashRepository
from royexa.identity_access.domain import Directory
from royexa.shared.calendar import BusinessCalendar


class CashDesk:
    def __init__(
        self, cash: CashRepository, directory: Directory, calendar: BusinessCalendar
    ) -> None:
        self._cash = cash
        self._directory = directory
        self._calendar = calendar

    def box_of(self, collector_id: str, now: datetime) -> CashBox:
        """The box a movement at `now` belongs to. A new box is saved on the spot, in the
        movement's own transaction, with the collector's float as opening balance."""
        day = self._calendar.day_of(now)
        box = self._cash.box_of_day(collector_id, day)
        if box is None:
            box = self._opened(collector_id, day)
            self._cash.save(box)
        return box

    def view(self, collector_id: str, day: date, now: datetime) -> CashBox:
        """Read side: a past day needs its box; today shows the box that its first movement
        will open when there is none yet. Nothing is written."""
        box = self._cash.box_of_day(collector_id, day)
        if box is not None:
            return box
        if day != self._calendar.day_of(now):
            raise NoOpenCashBox(collector_id)
        return self._opened(collector_id, day)

    def save(self, box: CashBox) -> None:
        self._cash.save(box)

    def _opened(self, collector_id: str, day: date) -> CashBox:
        opening = self._directory.opening_cash(collector_id)
        if opening is None or not self._calendar.is_collection_day(day):
            raise NoOpenCashBox(collector_id)
        return CashBox.open(collector_id, day, opening)
