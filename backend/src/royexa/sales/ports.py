from __future__ import annotations

from typing import Protocol, Self

from royexa.cash_box.ports import CashRepository
from royexa.ledger.ports import LedgerRepository
from royexa.loans.ports import LoanRepository
from royexa.sales.domain import Disbursement
from royexa.shared.outbox import Outbox


class DisbursementRepository(Protocol):
    def add(self, disbursement: Disbursement) -> None: ...
    def get(self, disbursement_id: str) -> Disbursement | None: ...
    def save(self, disbursement: Disbursement) -> None: ...


class SalesUnitOfWork(Protocol):
    """ADR-002: entry, deduction, schedule and outbox message commit together or not at all.
    Leaving the block without `commit` discards every write."""

    disbursements: DisbursementRepository
    loans: LoanRepository
    cash: CashRepository
    ledger: LedgerRepository
    outbox: Outbox

    def __enter__(self) -> Self: ...
    def __exit__(self, *exc_info: object) -> None: ...
    def commit(self) -> None: ...
