from typing import Protocol

from royexa.cash_box.domain import CashBox


class CashRepository(Protocol):
    def open_box_of(self, collector_id: str) -> CashBox | None: ...
    def save(self, box: CashBox) -> None: ...
