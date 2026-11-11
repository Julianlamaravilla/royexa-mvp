"""Loan queries (RF-05, CA-09): the schedule is derived when the loan is granted and read here."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Self

from dataclasses import dataclass
from datetime import date, datetime
from fractions import Fraction

from royexa.cash_box.ports import CashRepository
from royexa.clients.domain import ClientNotFound
from royexa.clients.ports import ClientRepository
from royexa.identity_access.domain import Directory, User
from royexa.ledger.ports import LedgerRepository
from royexa.ledger.posting import LedgerPosting
from royexa.loans.domain import (
    Loan,
    LoanNotFound,
    NonPayment,
    Payment,
    VisitNotAllowed,
)
from royexa.loans.ports import LoanRepository, NonPaymentRepository, PaymentRepository
from royexa.shared.clock import Clock
from royexa.shared.money import Money
from royexa.shared.payments import PaymentMethod


class LoansUnitOfWork(Protocol):
    clients: ClientRepository
    loans: LoanRepository

    def __enter__(self) -> Self: ...
    def __exit__(self, *exc_info: object) -> None: ...


class PaymentsUnitOfWork(LoansUnitOfWork, Protocol):
    """RF-01: balance, payment, ledger entry and box change together or not at all."""

    payments: PaymentRepository
    cash: CashRepository
    ledger: LedgerRepository

    def commit(self) -> None: ...


class RegisterPayment:
    """UC-05 (RF-01, RN-01): the collector of the route registers what a client paid."""

    def __init__(
        self, uow: Callable[[], PaymentsUnitOfWork], clock: Clock, directory: Directory
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._directory = directory

    def execute(
        self,
        actor: User,
        loan_id: str,
        amount: Money,
        method: PaymentMethod,
        device_time: datetime,
    ) -> tuple[Payment, Loan]:
        with self._uow() as uow:
            loan = uow.loans.get(loan_id)
            if loan is None:
                raise LoanNotFound(loan_id)
            client = uow.clients.get(loan.client_id)
            if client is None:
                raise ClientNotFound(loan.client_id)
            route = self._directory.route(client.route_id)
            now = self._clock.now()
            payment, updated = Payment.register(
                actor, route, loan, amount, method, device_time, now
            )
            uow.loans.save(updated)
            uow.payments.add(payment)
            LedgerPosting(uow.ledger, uow.cash).post_payment(
                payment.id, actor.id, amount, method, actor.id, device_time, now
            )
            uow.commit()
        return payment, updated


class PaymentQueries:
    def __init__(self, uow: Callable[[], PaymentsUnitOfWork]) -> None:
        self._uow = uow

    def for_loan(self, loan_id: str) -> list[Payment]:
        with self._uow() as uow:
            if uow.loans.get(loan_id) is None:
                raise LoanNotFound(loan_id)
            return uow.payments.for_loan(loan_id)


class VisitsUnitOfWork(LoansUnitOfWork, Protocol):
    payments: PaymentRepository
    non_payments: NonPaymentRepository

    def commit(self) -> None: ...


class RegisterNonPayment:
    """UC-06 (RF-01, CA-02, T3-P2): the collector records why a client did not pay."""

    def __init__(
        self, uow: Callable[[], VisitsUnitOfWork], clock: Clock, directory: Directory
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._directory = directory

    def execute(
        self,
        actor: User,
        loan_id: str,
        reason: str,
        commitment_date: date,
        device_time: datetime,
    ) -> NonPayment:
        with self._uow() as uow:
            loan = uow.loans.get(loan_id)
            if loan is None:
                raise LoanNotFound(loan_id)
            client = uow.clients.get(loan.client_id)
            if client is None:
                raise ClientNotFound(loan.client_id)
            route = self._directory.route(client.route_id)
            non_payment = NonPayment.register(
                actor, route, loan, reason, commitment_date, device_time, self._clock.now()
            )
            uow.non_payments.add(non_payment)
            uow.commit()
        return non_payment


@dataclass(frozen=True)
class PendingVisit:
    client_id: str
    client_name: str
    loan_id: str
    outstanding: Money
    remaining_installments: Fraction


class VisitQueries:
    """T3-P1: on a collection day, every client of the route with an active loan is pending
    until a payment or a non-payment is registered for that day."""

    COLLECTION_DAYS = range(1, 7)  # Monday to Saturday

    def __init__(
        self, uow: Callable[[], VisitsUnitOfWork], clock: Clock, directory: Directory
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._directory = directory

    def non_payments_of(self, loan_id: str) -> list[NonPayment]:
        with self._uow() as uow:
            if uow.loans.get(loan_id) is None:
                raise LoanNotFound(loan_id)
            return uow.non_payments.for_loan(loan_id)

    def pending(self, actor: User, route_id: str, day: date | None = None) -> list[PendingVisit]:
        route = self._directory.route(route_id)
        if not actor.is_admin and actor.id != route.collector_id:
            raise VisitNotAllowed(actor.id)
        day = day or self._clock.now().date()
        if day.isoweekday() not in self.COLLECTION_DAYS:
            return []
        pending = []
        with self._uow() as uow:
            for client in uow.clients.all():
                if client.route_id != route_id:
                    continue
                active = [loan for loan in uow.loans.for_client(client.id) if not loan.is_settled]
                if not active or any(self._visited(uow, loan.id, day) for loan in active):
                    continue
                loan = active[0]
                pending.append(
                    PendingVisit(
                        client.id,
                        client.name,
                        loan.id,
                        loan.outstanding,
                        loan.remaining_installments,
                    )
                )
        return pending

    @staticmethod
    def _visited(uow: VisitsUnitOfWork, loan_id: str, day: date) -> bool:
        return any(p.server_time.date() == day for p in uow.payments.for_loan(loan_id)) or any(
            n.server_time.date() == day for n in uow.non_payments.for_loan(loan_id)
        )


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
