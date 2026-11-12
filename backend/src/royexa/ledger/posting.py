"""Single writer of the ledger (ADR-001). It binds each entry to its cash box effect."""

from __future__ import annotations

from datetime import datetime

from royexa.cash_box.desk import CashDesk
from royexa.cash_box.domain import CashBox
from royexa.ledger.domain import CODE_EXPIRED_REASON, LedgerEntry, LedgerEntryType
from royexa.ledger.ports import LedgerRepository
from royexa.shared.ids import new_id
from royexa.shared.money import Money
from royexa.shared.payments import PaymentMethod


class LedgerPosting:
    def __init__(self, ledger: LedgerRepository, cash: CashDesk) -> None:
        self._ledger = ledger
        self._cash = cash

    def post_disbursement(
        self,
        disbursement_id: str,
        collector_id: str,
        amount: Money,
        actor_id: str,
        device_time: datetime,
        server_time: datetime,
    ) -> LedgerEntry:
        """CA-05, CA-07: the entry and the cash deduction belong to one unit of work."""
        box = self._box_of(collector_id, server_time)
        box.deduct(amount)
        self._cash.save(box)
        entry = LedgerEntry(
            new_id(),
            disbursement_id,
            LedgerEntryType.DISBURSEMENT,
            amount,
            box.id,
            actor_id,
            device_time,
            server_time,
        )
        self._ledger.append(entry)
        return entry

    def post_expired_attempt(
        self,
        disbursement_id: str,
        collector_id: str,
        amount: Money,
        actor_id: str,
        device_time: datetime,
        server_time: datetime,
    ) -> LedgerEntry:
        """CA-06: no deduction, one entry stating why."""
        box = self._box_of(collector_id, server_time)
        entry = LedgerEntry(
            new_id(),
            disbursement_id,
            LedgerEntryType.EXPIRED_ATTEMPT,
            amount,
            box.id,
            actor_id,
            device_time,
            server_time,
            CODE_EXPIRED_REASON,
        )
        self._ledger.append(entry)
        return entry

    def post_payment(
        self,
        payment_id: str,
        collector_id: str,
        amount: Money,
        method: PaymentMethod,
        actor_id: str,
        device_time: datetime,
        server_time: datetime,
    ) -> LedgerEntry:
        """RF-01: every payment leaves its entry; only cash moves the box (RES-01)."""
        box = self._box_of(collector_id, server_time)
        if method is PaymentMethod.CASH:
            box.collect(amount)
            self._cash.save(box)
        entry = LedgerEntry(
            new_id(),
            None,
            LedgerEntryType.PAYMENT,
            amount,
            box.id,
            actor_id,
            device_time,
            server_time,
            payment_id=payment_id,
            payment_method=method.value,
        )
        self._ledger.append(entry)
        return entry

    def _box_of(self, collector_id: str, now: datetime) -> CashBox:
        return self._cash.box_of(collector_id, now)
