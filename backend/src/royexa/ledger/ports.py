from typing import Protocol

from royexa.ledger.domain import LedgerEntry


class LedgerRepository(Protocol):
    """Insert and read only. RN-04: this port offers no way to change the past."""

    def append(self, entry: LedgerEntry) -> None: ...
    def for_disbursement(self, disbursement_id: str) -> list[LedgerEntry]: ...
    def all(self) -> list[LedgerEntry]: ...
