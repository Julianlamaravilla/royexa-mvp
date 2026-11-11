"""Immutable ledger entries (RF-04, RN-04, CA-07, INV-02)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from royexa.shared.errors import DomainError, WriteConflict
from royexa.shared.money import Money
from royexa.shared.payments import PaymentMethod

CODE_EXPIRED_REASON = "codigo_caducado"


class InvalidLedgerEntry(DomainError):
    pass


class DuplicateLedgerEntry(WriteConflict):
    """INV-02: one entry per disbursement and type. Raised on a uniqueness violation."""


class LedgerEntryType(StrEnum):
    DISBURSEMENT = "DESEMBOLSO"
    EXPIRED_ATTEMPT = "DESEMBOLSO_CADUCADO"
    PAYMENT = "PAGO"


@dataclass(frozen=True)
class LedgerEntry:
    id: str
    disbursement_id: str | None
    entry_type: LedgerEntryType
    amount: Money
    cash_box_id: str
    actor_id: str
    device_time: datetime
    server_time: datetime
    reason: str | None = None
    payment_id: str | None = None
    payment_method: str | None = None

    def __post_init__(self) -> None:
        if not self.amount.is_positive:
            raise InvalidLedgerEntry("the amount must be positive")
        if self.entry_type is LedgerEntryType.PAYMENT:
            if not self.payment_id or not self.payment_method or self.disbursement_id:
                raise InvalidLedgerEntry("a payment entry names its payment and its method")
        elif not self.disbursement_id or self.payment_id or self.payment_method:
            raise InvalidLedgerEntry("a disbursement entry names its disbursement")
        if self.entry_type is LedgerEntryType.EXPIRED_ATTEMPT and not self.reason:
            raise InvalidLedgerEntry("an expired attempt must state its reason (CA-06)")

    @property
    def cash_effect(self) -> Money:
        """RN-03: an expired attempt records the amount but releases nothing. A payment
        adds cash only when it was received in cash (RES-01)."""
        if self.entry_type is LedgerEntryType.DISBURSEMENT:
            return -self.amount
        if self.entry_type is LedgerEntryType.PAYMENT and self.payment_method == PaymentMethod.CASH:
            return self.amount
        return Money(0)

    @property
    def operation_id(self) -> str:
        """INV-02: the disbursement or the payment this entry settles; one entry of each
        type per operation."""
        return self.disbursement_id or self.payment_id or ""
