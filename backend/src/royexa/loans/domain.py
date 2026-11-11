"""Loans, installment schedule and the renewal rule (RF-05, RN-05, CA-09, CA-10)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from fractions import Fraction

from royexa.identity_access.domain import Route, User
from royexa.shared.errors import DomainError, NotFound
from royexa.shared.ids import new_id
from royexa.shared.money import InvalidAmount, Money
from royexa.shared.payments import PaymentMethod

SUNDAY = 7


class InvalidLoanTerms(DomainError):
    pass


class LoanNotFound(NotFound):
    pass


class PriorLoanNotSettled(DomainError):
    """RN-05 / CA-10: the previous loan still has a balance."""


class ExceptionNotAllowed(DomainError):
    """Only an administrator grants an RN-05 exception, and only over an unpaid loan."""


class ReasonRequired(DomainError):
    pass


class PaymentExceedsBalance(DomainError):
    """RN-01: a payment never exceeds the balance."""


class VisitNotAllowed(DomainError):
    """RF-01: only the collector of the route registers a visit; an administrator reads."""


class LoanAlreadySettled(DomainError):
    """CA-02: a non-payment is registered on a loan that still has a balance."""


class InvalidCommitmentDate(DomainError):
    """T3-P2: the commitment falls after the day of the registration."""


class PaymentNotAllowed(DomainError):
    """RF-01: the collector of the client's route registers the payment."""


def exact_decimal(value: Fraction) -> str:
    """The fractional counter without rounding (RN-01, EC-03): a finite decimal when there
    is one, otherwise the exact fraction."""
    denominator = value.denominator
    for factor in (2, 5):
        while denominator % factor == 0:
            denominator //= factor
    if denominator != 1:
        return f"{value.numerator}/{value.denominator}"
    return format((Decimal(value.numerator) / Decimal(value.denominator)).normalize(), "f")


@dataclass(frozen=True)
class LoanTerms:
    principal: Money
    term_days: int
    installment_count: int

    def __post_init__(self) -> None:
        if not self.principal.is_positive:
            raise InvalidLoanTerms("the amount must be positive")
        if self.installment_count < 1:
            raise InvalidLoanTerms("at least one installment is required")
        if self.term_days < self.installment_count:
            raise InvalidLoanTerms("the term must have one collection day per installment")


@dataclass(frozen=True)
class Installment:
    sequence: int
    due_date: date
    amount: Money
    paid: Money = Money(0)

    @property
    def pending(self) -> Money:
        return self.amount - self.paid


def collection_days_after(start: date, count: int) -> list[date]:
    """The next `count` collection days after `start`, Monday to Saturday (CA-09)."""
    days: list[date] = []
    current = start
    while len(days) < count:
        current += timedelta(days=1)
        if current.isoweekday() != SUNDAY:
            days.append(current)
    return days


def build_schedule(terms: LoanTerms, interest: Money, start: date) -> tuple[Installment, ...]:
    """Spread principal plus fixed interest over `term_days` collection days (CA-09)."""
    amounts = (terms.principal + interest).split(terms.installment_count)
    days = collection_days_after(start, terms.term_days)
    return tuple(
        Installment(
            sequence=number,
            due_date=days[number * terms.term_days // terms.installment_count - 1],
            amount=amount,
        )
        for number, amount in enumerate(amounts, start=1)
    )


@dataclass(frozen=True)
class Allocation:
    """The part of a payment that went to one installment."""

    sequence: int
    amount: Money


@dataclass(frozen=True)
class Loan:
    id: str
    client_id: str
    disbursement_id: str | None
    principal: Money
    interest: Money
    installments: tuple[Installment, ...]

    @classmethod
    def originate(
        cls, client_id: str, disbursement_id: str, terms: LoanTerms, interest: Money, start: date
    ) -> Loan:
        """A loan only exists once a disbursement is confirmed (RN-03)."""
        schedule = build_schedule(terms, interest, start)
        return cls(new_id(), client_id, disbursement_id, terms.principal, interest, schedule)

    @property
    def outstanding(self) -> Money:
        return sum((item.pending for item in self.installments), Money(0))

    @property
    def installment_count(self) -> int:
        return len(self.installments)

    @property
    def remaining_installments(self) -> Fraction:
        """RN-01: each installment counts for the share of it still owed, so 25 paid over
        an installment of 50 leaves 19.5 of 20."""
        return sum(
            (Fraction(item.pending.cents, item.amount.cents) for item in self.installments),
            Fraction(0),
        )

    @property
    def next_due_date(self) -> date | None:
        """The due date of the oldest installment still owed; none once the loan is settled."""
        return next((item.due_date for item in self.installments if item.pending.is_positive), None)

    def apply_payment(self, amount: Money) -> tuple[Loan, tuple[Allocation, ...]]:
        """RN-01: oldest installments first, the excess to the next, never past the balance.
        Returns the loan after the payment; this one is left as it was."""
        if not amount.is_positive:
            raise InvalidAmount("the payment must be positive")
        if amount > self.outstanding:
            raise PaymentExceedsBalance(self.id)
        left = amount.cents
        allocations: list[Allocation] = []
        installments: list[Installment] = []
        for item in self.installments:
            take = min(left, item.pending.cents)
            if take:
                allocations.append(Allocation(item.sequence, Money(take)))
                item = replace(item, paid=item.paid + Money(take))
                left -= take
            installments.append(item)
        return replace(self, installments=tuple(installments)), tuple(allocations)

    @property
    def is_settled(self) -> bool:
        return not self.outstanding.is_positive


@dataclass(frozen=True)
class Payment:
    """Money received on a loan, in cash or by transfer (RF-01, RES-01)."""

    id: str
    loan_id: str
    client_id: str
    collector_id: str
    amount: Money
    method: PaymentMethod
    device_time: datetime
    server_time: datetime
    allocations: tuple[Allocation, ...] = field(default_factory=tuple)

    @classmethod
    def register(
        cls,
        actor: User,
        route: Route,
        loan: Loan,
        amount: Money,
        method: PaymentMethod,
        device_time: datetime,
        now: datetime,
    ) -> tuple[Payment, Loan]:
        if actor.id != route.collector_id:
            raise PaymentNotAllowed(actor.id)
        updated, allocations = loan.apply_payment(amount)
        payment = cls(
            new_id(),
            loan.id,
            loan.client_id,
            actor.id,
            amount,
            method,
            device_time,
            now,
            allocations,
        )
        return payment, updated


@dataclass(frozen=True)
class NonPayment:
    """A visit that collected nothing (RF-01, CA-02). It changes no balance and moves no
    money; it only ends the day's pending visit and records why and until when (T3-P2)."""

    id: str
    loan_id: str
    client_id: str
    collector_id: str
    reason: str
    commitment_date: date
    device_time: datetime
    server_time: datetime

    @classmethod
    def register(
        cls,
        actor: User,
        route: Route,
        loan: Loan,
        reason: str,
        commitment_date: date,
        device_time: datetime,
        now: datetime,
    ) -> NonPayment:
        if actor.id != route.collector_id:
            raise VisitNotAllowed(actor.id)
        if loan.is_settled:
            raise LoanAlreadySettled(loan.id)
        if not reason.strip():
            raise ReasonRequired("a non-payment needs a reason")
        if commitment_date <= now.date():
            raise InvalidCommitmentDate(commitment_date.isoformat())
        return cls(
            new_id(),
            loan.id,
            loan.client_id,
            actor.id,
            reason.strip(),
            commitment_date,
            device_time,
            now,
        )


@dataclass
class RenewalException:
    """RN-05: the explicit, registered, single-use administrator authorization."""

    id: str
    client_id: str
    prior_loan_id: str
    granted_by: str
    reason: str
    granted_at: datetime
    consumed_by: str | None = None

    @classmethod
    def grant(cls, actor: User, prior: Loan | None, reason: str, now: datetime) -> RenewalException:
        if not actor.is_admin:
            raise ExceptionNotAllowed("only an administrator can grant the exception")
        if prior is None:
            raise ExceptionNotAllowed("the client has no unsettled loan")
        if not reason.strip():
            raise ReasonRequired("the exception needs a reason")
        return cls(new_id(), prior.client_id, prior.id, actor.id, reason, now)

    def consume(self, disbursement_id: str) -> None:
        self.consumed_by = disbursement_id


def ensure_renewal_allowed(prior: Loan | None, exception: RenewalException | None) -> None:
    """RN-05: pass only when no balance exists or an exception covers that exact loan."""
    if prior is None:
        return
    if exception is None or exception.prior_loan_id != prior.id:
        raise PriorLoanNotSettled(prior.id)
