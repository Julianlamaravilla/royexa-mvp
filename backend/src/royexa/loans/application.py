"""Loan queries (RF-05, CA-09): the schedule is derived when the loan is granted and read here."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Self

from dataclasses import dataclass
from datetime import date, datetime
from fractions import Fraction

from royexa.cash_box.desk import CashDesk
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
from royexa.shared.calendar import BusinessCalendar
from royexa.shared.clock import Clock
from royexa.shared.money import Money
from royexa.shared.outbox import Outbox, OutboxMessage
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
    outbox: Outbox

    def commit(self) -> None: ...


class RegisterPayment:
    """UC-05 (RF-01, RN-01): the collector of the route registers what a client paid."""

    def __init__(
        self,
        uow: Callable[[], PaymentsUnitOfWork],
        clock: Clock,
        directory: Directory,
        calendar: BusinessCalendar,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._directory = directory
        self._calendar = calendar

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
            LedgerPosting(
                uow.ledger, CashDesk(uow.cash, self._directory, self._calendar)
            ).post_payment(
                payment.id, actor.id, amount, method, actor.id, device_time, now
            )
            uow.outbox.add(
                OutboxMessage.enqueue_payment_receipt(
                    payment.client_id, payment.id, now, _receipt_payload(payment, updated)
                )
            )
            uow.commit()
        return payment, updated


def _receipt_payload(payment: Payment, loan: Loan) -> dict[str, str]:
    """CA-11: the amount received, the balance left and the next due date (empty once the
    loan is settled)."""
    due = loan.next_due_date
    return {
        "amount_cents": str(payment.amount.cents),
        "outstanding_cents": str(loan.outstanding.cents),
        "next_due_date": due.isoformat() if due else "",
    }


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
        self,
        uow: Callable[[], VisitsUnitOfWork],
        clock: Clock,
        directory: Directory,
        calendar: BusinessCalendar,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._directory = directory
        self._calendar = calendar

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
            now = self._clock.now()
            non_payment = NonPayment.register(
                actor,
                route,
                loan,
                reason,
                commitment_date,
                device_time,
                now,
                self._calendar.day_of(now),
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


@dataclass(frozen=True)
class PaidClient:
    client_id: str
    client_name: str
    cash: Money
    transfer: Money
    payments: int


@dataclass(frozen=True)
class UnpaidClient:
    client_id: str
    client_name: str
    loan_id: str
    reason: str
    commitment_date: date


@dataclass(frozen=True)
class DayPanels:
    """RF-02: the three panels of a collector's day. A client is in one panel at most:
    paid wins over did-not-pay, and either ends his pending visit."""

    day: date
    collector_id: str
    route_id: str
    pending: list[PendingVisit]
    paid: list[PaidClient]
    unpaid: list[UnpaidClient]

    @property
    def cash_total(self) -> Money:
        return sum((item.cash for item in self.paid), Money(0))

    @property
    def transfer_total(self) -> Money:
        return sum((item.transfer for item in self.paid), Money(0))


def pending_visits(
    uow: VisitsUnitOfWork, calendar: BusinessCalendar, route_id: str, day: date
) -> list[PendingVisit]:
    """T3-P1: on a collection day, every client of the route with an active loan is pending
    until a payment or a non-payment is registered for that day. Reads inside the caller's
    transaction, so the close of a box and its pending check see the same data."""
    if not calendar.is_collection_day(day):
        return []

    def visited(loans: list[Loan]) -> bool:
        """A payment or a non-payment on any loan of the client ends his visit (T3-P1)."""
        return any(
            calendar.day_of(p.server_time) == day
            for loan in loans
            for p in uow.payments.for_loan(loan.id)
        ) or any(
            calendar.day_of(n.server_time) == day
            for loan in loans
            for n in uow.non_payments.for_loan(loan.id)
        )

    pending = []
    for client in uow.clients.all():
        if client.route_id != route_id:
            continue
        loans = uow.loans.for_client(client.id)
        active = [loan for loan in loans if not loan.is_settled]
        if not active or visited(loans):
            continue
        loan = active[0]
        pending.append(
            PendingVisit(
                client.id, client.name, loan.id, loan.outstanding, loan.remaining_installments
            )
        )
    return pending


class VisitQueries:
    """T3-P1: who is pending a visit on a day, read for the collector or an administrator."""

    def __init__(
        self,
        uow: Callable[[], VisitsUnitOfWork],
        clock: Clock,
        directory: Directory,
        calendar: BusinessCalendar,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._directory = directory
        self._calendar = calendar

    def non_payments_of(self, loan_id: str) -> list[NonPayment]:
        with self._uow() as uow:
            if uow.loans.get(loan_id) is None:
                raise LoanNotFound(loan_id)
            return uow.non_payments.for_loan(loan_id)

    def pending(self, actor: User, route_id: str, day: date | None = None) -> list[PendingVisit]:
        route = self._directory.route(route_id)
        if not actor.is_admin and actor.id != route.collector_id:
            raise VisitNotAllowed(actor.id)
        day = day or self._calendar.day_of(self._clock.now())
        with self._uow() as uow:
            return pending_visits(uow, self._calendar, route_id, day)

    def panels(self, actor: User, collector_id: str) -> DayPanels:
        """The panels of today for the collector's route; read by the collector or an
        administrator. Only today: a past day's pending list would need that day's state."""
        if not actor.is_admin and actor.id != collector_id:
            raise VisitNotAllowed(actor.id)
        route = self._directory.route_of_collector(collector_id)
        day = self._calendar.day_of(self._clock.now())
        if not self._calendar.is_collection_day(day):
            return DayPanels(day, collector_id, route.id, [], [], [])
        paid: list[PaidClient] = []
        unpaid: list[UnpaidClient] = []
        with self._uow() as uow:
            pending = pending_visits(uow, self._calendar, route.id, day)
            for client in uow.clients.all():
                if client.route_id != route.id:
                    continue
                loans = uow.loans.for_client(client.id)
                payments = [
                    p
                    for loan in loans
                    for p in uow.payments.for_loan(loan.id)
                    if self._calendar.day_of(p.server_time) == day
                ]
                if payments:
                    paid.append(self._paid(client.id, client.name, payments))
                    continue
                refusals = [
                    (loan, n)
                    for loan in loans
                    for n in uow.non_payments.for_loan(loan.id)
                    if self._calendar.day_of(n.server_time) == day
                ]
                if refusals:
                    loan, last = refusals[-1]
                    unpaid.append(
                        UnpaidClient(
                            client.id, client.name, loan.id, last.reason, last.commitment_date
                        )
                    )
        return DayPanels(day, collector_id, route.id, pending, paid, unpaid)

    @staticmethod
    def _paid(client_id: str, name: str, payments: list[Payment]) -> PaidClient:
        def total(method: PaymentMethod) -> Money:
            return sum((p.amount for p in payments if p.method is method), Money(0))

        return PaidClient(
            client_id, name, total(PaymentMethod.CASH), total(PaymentMethod.TRANSFER), len(payments)
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
