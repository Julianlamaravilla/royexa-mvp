"""Immutable ledger entries (RF-04, RN-04, CA-07, INV-02)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from royexa.shared.errors import DomainError, WriteConflict
from royexa.shared.money import Money

CODE_EXPIRED_REASON = "codigo_caducado"


class InvalidLedgerEntry(DomainError):
    pass


class DuplicateLedgerEntry(WriteConflict):
    """INV-02: one entry per disbursement and type. Raised on a uniqueness violation."""


class LedgerEntryType(StrEnum):
    DISBURSEMENT = "DESEMBOLSO"
    EXPIRED_ATTEMPT = "DESEMBOLSO_CADUCADO"


@dataclass(frozen=True)
class LedgerEntry:
    id: str
    disbursement_id: str
    entry_type: LedgerEntryType
    amount: Money
    cash_box_id: str
    actor_id: str
    device_time: datetime
    server_time: datetime
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.amount.is_positive:
            raise InvalidLedgerEntry("the amount must be positive")
        if self.entry_type is LedgerEntryType.EXPIRED_ATTEMPT and not self.reason:
            raise InvalidLedgerEntry("an expired attempt must state its reason (CA-06)")

    @property
    def cash_effect(self) -> Money:
        """RN-03: an expired attempt records the amount but releases nothing."""
        if self.entry_type is LedgerEntryType.DISBURSEMENT:
            return -self.amount
        return Money(0)
