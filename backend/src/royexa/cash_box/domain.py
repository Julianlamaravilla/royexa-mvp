"""Cash box of a collector (RF-02, RN-03). Closing is Entrega 4; a closed box stays closed."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from royexa.identity_access.domain import User
from royexa.shared.errors import DomainError, NotFound
from royexa.shared.ids import new_id
from royexa.shared.money import InvalidAmount, Money


class CashBoxClosed(DomainError):
    """RN-02: a closed box takes no further movement."""


class NoOpenCashBox(NotFound):
    pass


class CashCloseNotAllowed(DomainError):
    """RF-02: the collector of the box closes it; nobody else."""


class PendingVisitsRemain(DomainError):
    """CA-04, RN-02: a box with clients still pending a visit does not close."""


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

    def close(self) -> None:
        """RN-02: irreversible. A closed box is never reopened or edited."""
        self.ensure_open()
        self.closed = True


@dataclass(frozen=True)
class CashClose:
    """The close of one day's box (RF-02, CA-03): what the ledger says should be delivered,
    what the collector delivered, and the signed difference (T5-P1)."""

    id: str
    cash_box_id: str
    collector_id: str
    day: date
    expected: Money
    delivered: Money
    closed_by: str
    device_time: datetime
    server_time: datetime

    @property
    def discrepancy(self) -> Money:
        """Delivered minus expected; zero is not a discrepancy (RF-07)."""
        return self.delivered - self.expected

    @classmethod
    def settle(
        cls,
        box: CashBox,
        actor: User,
        expected: Money,
        delivered: Money,
        device_time: datetime,
        now: datetime,
    ) -> CashClose:
        if actor.id != box.collector_id:
            raise CashCloseNotAllowed(actor.id)
        if delivered.cents < 0:
            raise InvalidAmount("what is delivered is never negative")
        return cls(
            new_id(), box.id, box.collector_id, box.day, expected, delivered, actor.id,
            device_time, now,
        )
