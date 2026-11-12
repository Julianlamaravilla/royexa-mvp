"""Disbursement use cases (UC-01 to UC-04). They coordinate; the aggregates decide."""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from royexa.cash_box.desk import CashDesk
from royexa.cash_box.domain import CashBox
from royexa.clients.domain import ClientNotFound
from royexa.identity_access.domain import Directory, User
from royexa.ledger.domain import LedgerEntry
from royexa.ledger.posting import LedgerPosting
from royexa.loans.domain import Loan, LoanTerms, RenewalException, ensure_renewal_allowed
from royexa.sales.domain import (
    ApprovalRefused,
    ConfirmationCodeExpired,
    ConfirmationOutcome,
    Disbursement,
    DisbursementNotFound,
)
from royexa.sales.ports import SalesUnitOfWork
from royexa.shared.calendar import BusinessCalendar
from royexa.shared.clock import Clock
from royexa.shared.errors import WriteConflict
from royexa.shared.ids import new_id
from royexa.shared.outbox import NoticeKind, OutboxMessage

CODE_BYTES = 4


def generate_code() -> str:
    return secrets.token_hex(CODE_BYTES).upper()


@dataclass(frozen=True)
class SalesContext:
    uow: Callable[[], SalesUnitOfWork]
    clock: Clock
    directory: Directory
    code_ttl: timedelta
    new_code: Callable[[], str] = generate_code
    calendar: BusinessCalendar = field(default_factory=lambda: BusinessCalendar.in_zone("UTC"))

    def cash_desk(self, uow: SalesUnitOfWork) -> CashDesk:
        return CashDesk(uow.cash, self.directory, self.calendar)


def _client(uow: SalesUnitOfWork, client_id: str):
    client = uow.clients.get(client_id)
    if client is None:
        raise ClientNotFound(client_id)
    return client


def _load(uow: SalesUnitOfWork, disbursement_id: str) -> Disbursement:
    disbursement = uow.disbursements.get(disbursement_id)
    if disbursement is None:
        raise DisbursementNotFound(disbursement_id)
    return disbursement


class RequestDisbursement:
    """UC-01. RF-03, flow steps 1 to 3."""

    def __init__(self, context: SalesContext) -> None:
        self._context = context

    def execute(self, actor: User, client_id: str, terms: LoanTerms) -> Disbursement:
        context = self._context
        with context.uow() as uow:
            client = _client(uow, client_id)
            route = context.directory.route(client.route_id)
            collector = context.directory.user(route.collector_id)
            prior = uow.loans.unsettled_for_client(client.id)
            exception = uow.loans.open_exception_for(client.id) if prior else None
            disbursement = Disbursement.request(
                new_id(),
                client,
                route,
                collector,
                actor,
                terms,
                context.clock.now(),
                exception.id if exception else None,
            )
            ensure_renewal_allowed(prior, exception)
            if exception:
                exception.consume(disbursement.id)
                uow.loans.save_exception(exception)
            uow.disbursements.add(disbursement)
            uow.commit()
        return disbursement


class ApproveDisbursement:
    """UC-02. RF-03, RN-06, EC-02, flow steps 4 and 5."""

    def __init__(self, context: SalesContext) -> None:
        self._context = context

    def execute(self, actor: User, disbursement_id: str, reason: str | None = None) -> Disbursement:
        context = self._context
        now = context.clock.now()
        plain_code = context.new_code()
        with context.uow() as uow:
            disbursement = _load(uow, disbursement_id)
            try:
                disbursement.approve(actor, plain_code, now, context.code_ttl, reason)
            except ApprovalRefused:
                # RN-06: the refusal is a fact to keep, not a failure to roll back.
                uow.disbursements.save(disbursement)
                uow.commit()
                raise
            uow.disbursements.save(disbursement)
            uow.outbox.add(
                OutboxMessage.enqueue(
                    NoticeKind.CONFIRMATION_CODE,
                    disbursement.client_id,
                    disbursement.id,
                    now,
                    {"code": plain_code},
                )
            )
            uow.commit()
        return disbursement


class RejectDisbursement:
    """UC-02, alternative outcome. RF-03, flow step 4."""

    def __init__(self, context: SalesContext) -> None:
        self._context = context

    def execute(self, actor: User, disbursement_id: str, reason: str) -> Disbursement:
        with self._context.uow() as uow:
            disbursement = _load(uow, disbursement_id)
            disbursement.reject(actor, reason, self._context.clock.now())
            uow.disbursements.save(disbursement)
            uow.commit()
        return disbursement


class ConfirmDisbursement:
    """UC-03. RN-03, RN-04, CA-05, CA-06, ADR-004."""

    def __init__(self, context: SalesContext) -> None:
        self._context = context

    def execute(
        self, actor: User, disbursement_id: str, plain_code: str, device_time: datetime
    ) -> Disbursement:
        try:
            return self._attempt(actor, disbursement_id, plain_code, device_time)
        except WriteConflict:
            # ADR-004: the loser re-reads what was committed. Against the same disbursement
            # that is a replay, so it reports the first result with no second effect.
            return self._attempt(actor, disbursement_id, plain_code, device_time)

    def _attempt(
        self, actor: User, disbursement_id: str, plain_code: str, device_time: datetime
    ) -> Disbursement:
        context = self._context
        with context.uow() as uow:
            disbursement = _load(uow, disbursement_id)
            now = context.clock.now()
            outcome = disbursement.confirm(plain_code, actor, now)
            if outcome is ConfirmationOutcome.CONFIRMED:
                self._settle(uow, disbursement, actor, device_time, now)
            elif outcome is ConfirmationOutcome.EXPIRED:
                self._record_expiry(uow, disbursement, actor, device_time, now)
            if not outcome.is_replay:
                uow.disbursements.save(disbursement)
                uow.commit()
        if outcome.is_expiry:
            raise ConfirmationCodeExpired(disbursement_id)
        return disbursement

    def _settle(
        self,
        uow: SalesUnitOfWork,
        disbursement: Disbursement,
        actor: User,
        device_time: datetime,
        now: datetime,
    ) -> None:
        """CA-05: entry, cash deduction, schedule and receipt in one unit of work.
        RN-05 runs again here: another request for the client may have settled first."""
        exception_id = disbursement.renewal_exception_id
        ensure_renewal_allowed(
            uow.loans.unsettled_for_client(disbursement.client_id),
            uow.loans.get_exception(exception_id) if exception_id else None,
        )
        loan = Loan.originate(
            disbursement.client_id,
            disbursement.id,
            disbursement.terms,
            disbursement.interest,
            now.date(),
        )
        uow.loans.add(loan)
        disbursement.attach_loan(loan.id)
        LedgerPosting(uow.ledger, self._context.cash_desk(uow)).post_disbursement(
            disbursement.id,
            disbursement.collector_id,
            disbursement.terms.principal,
            actor.id,
            device_time,
            now,
        )
        uow.outbox.add(
            OutboxMessage.enqueue(
                NoticeKind.DISBURSEMENT_RECEIPT, disbursement.client_id, disbursement.id, now
            )
        )

    def _record_expiry(
        self,
        uow: SalesUnitOfWork,
        disbursement: Disbursement,
        actor: User,
        device_time: datetime,
        now: datetime,
    ) -> None:
        """CA-06: the attempt stays on record with its reason and no money moves."""
        LedgerPosting(uow.ledger, self._context.cash_desk(uow)).post_expired_attempt(
            disbursement.id,
            disbursement.collector_id,
            disbursement.terms.principal,
            actor.id,
            device_time,
            now,
        )


class GrantRenewalException:
    """UC-04. RN-05, CA-10: the administrator authorizes the renewal expressly."""

    def __init__(self, context: SalesContext) -> None:
        self._context = context

    def execute(self, actor: User, client_id: str, reason: str) -> RenewalException:
        context = self._context
        with context.uow() as uow:
            client = _client(uow, client_id)
            prior = uow.loans.unsettled_for_client(client.id)
            exception = RenewalException.grant(actor, prior, reason, context.clock.now())
            uow.loans.add_exception(exception)
            uow.commit()
        return exception


@dataclass(frozen=True)
class DisbursementDetail:
    disbursement: Disbursement
    loan: Loan | None
    entries: list[LedgerEntry]


class SalesQueries:
    """Read side of the slice: CA-05, CA-07 and CA-06 are observed through it."""

    def __init__(
        self,
        uow: Callable[[], SalesUnitOfWork],
        clock: Clock,
        directory: Directory,
        calendar: BusinessCalendar,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._directory = directory
        self._calendar = calendar

    def detail(self, disbursement_id: str) -> DisbursementDetail:
        with self._uow() as uow:
            disbursement = _load(uow, disbursement_id)
            loan = uow.loans.get(disbursement.loan_id) if disbursement.loan_id else None
            return DisbursementDetail(
                disbursement, loan, uow.ledger.for_disbursement(disbursement_id)
            )

    def ledger(self, disbursement_id: str | None = None) -> list[LedgerEntry]:
        with self._uow() as uow:
            if disbursement_id is None:
                return uow.ledger.all()
            return uow.ledger.for_disbursement(disbursement_id)

    def cash_box(self, collector_id: str, day: date | None = None) -> CashBox:
        """The box of a day (today by default). T5-P2: today's box shows its opening state
        before the first movement; a day without movements has no box."""
        now = self._clock.now()
        with self._uow() as uow:
            desk = CashDesk(uow.cash, self._directory, self._calendar)
            return desk.view(collector_id, day or self._calendar.day_of(now), now)

