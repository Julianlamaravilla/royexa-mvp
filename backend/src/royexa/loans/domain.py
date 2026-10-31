"""Loans, installment schedule and the renewal rule (RF-05, RN-05, CA-09, CA-10)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from royexa.identity_access.domain import User
from royexa.shared.errors import DomainError
from royexa.shared.ids import new_id
from royexa.shared.money import Money

SUNDAY = 7


class InvalidLoanTerms(DomainError):
    pass


class PriorLoanNotSettled(DomainError):
    """RN-05 / CA-10: the previous loan still has a balance."""


class ExceptionNotAllowed(DomainError):
    """Only an administrator grants an RN-05 exception, and only over an unpaid loan."""


class ReasonRequired(DomainError):
    pass


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
    def is_settled(self) -> bool:
        return not self.outstanding.is_positive


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
