"""Loan queries (RF-05, CA-09): the schedule is derived when the loan is granted and read here."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Self

from royexa.clients.domain import ClientNotFound
from royexa.clients.ports import ClientRepository
from royexa.loans.domain import Loan, LoanNotFound
from royexa.loans.ports import LoanRepository


class LoansUnitOfWork(Protocol):
    clients: ClientRepository
    loans: LoanRepository

    def __enter__(self) -> Self: ...
    def __exit__(self, *exc_info: object) -> None: ...


class LoanQueries:
    def __init__(self, uow: Callable[[], LoansUnitOfWork]) -> None:
        self._uow = uow

    def get(self, loan_id: str) -> Loan:
        with self._uow() as uow:
            loan = uow.loans.get(loan_id)
        if loan is None:
            raise LoanNotFound(loan_id)
        return loan

    def for_client(self, client_id: str) -> list[Loan]:
        with self._uow() as uow:
            if uow.clients.get(client_id) is None:
                raise ClientNotFound(client_id)
            return uow.loans.for_client(client_id)
