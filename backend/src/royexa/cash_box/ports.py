from datetime import date
from typing import Protocol

from royexa.cash_box.domain import CashBox


class CashRepository(Protocol):
    def box_of_day(self, collector_id: str, day: date) -> CashBox | None: ...
    def save(self, box: CashBox) -> None: ...
