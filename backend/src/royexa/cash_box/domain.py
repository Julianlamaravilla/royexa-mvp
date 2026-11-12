"""Cash box of a collector (RF-02, RN-03). Closing is Entrega 4; a closed box stays closed."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from royexa.shared.errors import DomainError, NotFound
from royexa.shared.money import Money


class CashBoxClosed(DomainError):
    """RN-02: a closed box takes no further movement."""


class NoOpenCashBox(NotFound):
    pass


@dataclass
class CashBox:
    id: str
    collector_id: str
    day: date
    opening_balance: Money
    balance: Money
    closed: bool = False

    @classmethod
    def open(cls, collector_id: str, day: date, opening_balance: Money) -> CashBox:
        """T5-P2: one box per collector and day."""
        return cls(f"caja-{collector_id}-{day.isoformat()}", collector_id, day, opening_balance, opening_balance)

    def ensure_open(self) -> None:
        if self.closed:
            raise CashBoxClosed(self.id)

    def deduct(self, amount: Money) -> None:
        """RN-03: only a confirmed disbursement reaches this point."""
        self.ensure_open()
        self.balance = self.balance - amount

    def collect(self, amount: Money) -> None:
        """RF-01: cash received on a payment. Transfers never reach this point (RES-01)."""
        self.ensure_open()
        self.balance = self.balance + amount
