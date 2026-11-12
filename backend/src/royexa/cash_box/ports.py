from datetime import date
from typing import Protocol

from royexa.cash_box.domain import CashBox, CashClose


class CashRepository(Protocol):
    def box_of_day(self, collector_id: str, day: date) -> CashBox | None: ...
    def get(self, box_id: str) -> CashBox | None: ...
    def save(self, box: CashBox) -> None: ...
    def open_between(self, since: date, until: date) -> list[CashBox]:
        """Boxes not closed whose day is in the range, by day and collector."""
        ...


class CashCloseRepository(Protocol):
    def add(self, close: CashClose) -> None:
        """One close per box; a second one fails as a write conflict."""
        ...

    def all(self, collector_id: str | None = None, day: date | None = None) -> list[CashClose]:
        """In the order they were recorded."""
        ...
