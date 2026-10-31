"""Disbursement aggregate (RF-03). Owns RN-03 and RN-06; EC-02 admits no exception."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, StrEnum

from royexa.clients.domain import Client
from royexa.identity_access.domain import Role, Route, User
from royexa.loans.domain import LoanTerms, ReasonRequired
from royexa.shared.errors import DomainError, NotFound
from royexa.shared.money import Money


class DisbursementStatus(StrEnum):
    REQUESTED = "SOLICITADO"
    PENDING_AUTHORIZATION = "EN_ESPERA_AUTORIZACION"
    APPROVED = "APROBADO"
    REJECTED = "RECHAZADO"
    CONFIRMED = "CONFIRMADO"
    EXPIRED = "CADUCADO"


AWAITING_DECISION = frozenset(
    {DisbursementStatus.REQUESTED, DisbursementStatus.PENDING_AUTHORIZATION}
)


class ConfirmationOutcome(Enum):
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    ALREADY_CONFIRMED = "already_confirmed"
    ALREADY_EXPIRED = "already_expired"

    @property
    def is_replay(self) -> bool:
        return self in (self.ALREADY_CONFIRMED, self.ALREADY_EXPIRED)

    @property
    def is_expiry(self) -> bool:
        return self in (self.EXPIRED, self.ALREADY_EXPIRED)


class DisbursementNotFound(NotFound):
    pass


class InvalidTransition(DomainError):
    """ADR-004: a state only moves along the allowed transitions."""


class RequesterNotAllowed(DomainError):
    pass


class ClientOutsideRoute(DomainError):
    """Flow step 1: a collector requests only for clients of their route."""


class AmountExceedsRouteLimit(DomainError):
    """Flow step 2: the amount must fit the route limits."""


class ApprovalRefused(DomainError):
    """The attempt was refused and recorded with the identity of its author."""


class SelfApprovalForbidden(ApprovalRefused):
    """RN-06, EC-02: whoever originated the request cannot approve it."""


class ApproverRoleRequired(ApprovalRefused):
    """Only an administrator approves."""


class DeciderRoleRequired(DomainError):
    """Only an administrator rejects."""


class ValidatorNotAllowed(DomainError):
    """CA-05: the collector of the route validates the code."""


class InvalidConfirmationCode(DomainError):
    pass


class ConfirmationCodeExpired(DomainError):
    """CA-06: raised after the attempt was recorded."""


@dataclass(frozen=True)
class ConfirmationCode:
    """RN-03: tied to one operation and one client, with an expiry. Stored as a digest."""

    digest: str
    expires_at: datetime

    @staticmethod
    def _digest(plain: str, disbursement_id: str, client_id: str) -> str:
        material = f"{disbursement_id}|{client_id}|{plain}".encode()
        return hashlib.sha256(material).hexdigest()

    @classmethod
    def issue(
        cls,
        plain: str,
        disbursement_id: str,
        client_id: str,
        issued_at: datetime,
        ttl: timedelta,
    ) -> ConfirmationCode:
        return cls(cls._digest(plain, disbursement_id, client_id), issued_at + ttl)

    def matches(self, plain: str, disbursement_id: str, client_id: str) -> bool:
        return hmac.compare_digest(self.digest, self._digest(plain, disbursement_id, client_id))

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at


@dataclass(frozen=True)
class RefusedApprovalAttempt:
    """RN-06: who tried, when and why it was refused."""

    actor_id: str
    actor_role: Role
    at: datetime
    reason: str


_IMMUTABLE_FIELDS = frozenset({"id", "client_id", "requested_by", "requested_at"})


@dataclass
class Disbursement:
    id: str
    client_id: str
    route_id: str
    collector_id: str
    requested_by: str
    requested_at: datetime
    terms: LoanTerms
    interest: Money
    status: DisbursementStatus
    renewal_exception_id: str | None = None
    approved_by: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None
    decision_reason: str | None = None
    code: ConfirmationCode | None = None
    confirmed_by: str | None = None
    resolved_at: datetime | None = None
    loan_id: str | None = None
    refused_approval_attempts: list[RefusedApprovalAttempt] = field(default_factory=list)

    def __setattr__(self, name: str, value: object) -> None:
        # ALT-06B: who originated the request is the input of RN-06 and cannot change.
        if name in _IMMUTABLE_FIELDS and name in self.__dict__:
            raise AttributeError(f"{name} is immutable")
        object.__setattr__(self, name, value)

    @classmethod
    def request(
        cls,
        disbursement_id: str,
        client: Client,
        route: Route,
        collector: User,
        actor: User,
        terms: LoanTerms,
        now: datetime,
        renewal_exception_id: str | None = None,
    ) -> Disbursement:
        """Flow steps 1 to 3: within the route limit; above the collector limit it waits."""
        if actor.role is Role.COLLECTOR and actor.id != route.collector_id:
            raise ClientOutsideRoute(client.id)
        if actor.role not in (Role.COLLECTOR, Role.ADMIN):
            raise RequesterNotAllowed(actor.id)
        if terms.principal > route.max_disbursement:
            raise AmountExceedsRouteLimit(route.id)
        limit = collector.disbursement_limit
        over_limit = limit is not None and terms.principal > limit
        return cls(
            id=disbursement_id,
            client_id=client.id,
            route_id=route.id,
            collector_id=collector.id,
            requested_by=actor.id,
            requested_at=now,
            terms=terms,
            interest=terms.principal.fraction_bps(route.interest_bps),
            status=(
                DisbursementStatus.PENDING_AUTHORIZATION
                if over_limit
                else DisbursementStatus.REQUESTED
            ),
            renewal_exception_id=renewal_exception_id,
        )

    def approve(
        self,
        actor: User,
        plain_code: str,
        now: datetime,
        code_ttl: timedelta,
        reason: str | None = None,
    ) -> None:
        """Flow steps 4 and 5. RN-06 runs first: every refused attempt leaves its identity,
        and no code exists unless every guard passed (EC-02)."""
        self._ensure_may_approve(actor, now)
        self._ensure_awaiting_decision()
        if self.status is DisbursementStatus.PENDING_AUTHORIZATION and not (reason or "").strip():
            raise ReasonRequired("authorizing an amount over the collector limit needs a reason")
        self.status = DisbursementStatus.APPROVED
        self.approved_by = actor.id
        self.decided_by = actor.id
        self.decided_at = now
        self.decision_reason = reason
        self.code = ConfirmationCode.issue(plain_code, self.id, self.client_id, now, code_ttl)

    def reject(self, actor: User, reason: str, now: datetime) -> None:
        """Flow step 4: a rejection always states its reason."""
        if not actor.is_admin:
            raise DeciderRoleRequired(actor.id)
        self._ensure_awaiting_decision()
        if not reason.strip():
            raise ReasonRequired("a rejection needs a reason")
        self.status = DisbursementStatus.REJECTED
        self.decided_by = actor.id
        self.decided_at = now
        self.decision_reason = reason

    def confirm(self, plain_code: str, actor: User, now: datetime) -> ConfirmationOutcome:
        """RN-03. A terminal state reports the first result and never transitions again
        (ADR-004); the code is checked first so a wrong code learns nothing."""
        if actor.id != self.collector_id:
            raise ValidatorNotAllowed(actor.id)
        if self.code is None or self.status is DisbursementStatus.REJECTED:
            raise InvalidTransition(self.status)
        if not self.code.matches(plain_code, self.id, self.client_id):
            raise InvalidConfirmationCode(self.id)
        if self.status is DisbursementStatus.CONFIRMED:
            return ConfirmationOutcome.ALREADY_CONFIRMED
        if self.status is DisbursementStatus.EXPIRED:
            return ConfirmationOutcome.ALREADY_EXPIRED
        if self.code.is_expired(now):
            self.status = DisbursementStatus.EXPIRED
            self.resolved_at = now
            return ConfirmationOutcome.EXPIRED
        self.status = DisbursementStatus.CONFIRMED
        self.confirmed_by = actor.id
        self.resolved_at = now
        return ConfirmationOutcome.CONFIRMED

    def attach_loan(self, loan_id: str) -> None:
        if self.status is not DisbursementStatus.CONFIRMED:
            raise InvalidTransition(self.status)
        self.loan_id = loan_id

    def _ensure_may_approve(self, actor: User, now: datetime) -> None:
        if actor.id == self.requested_by:
            self._record_refusal(actor, now, "quien_origina_no_aprueba")
            raise SelfApprovalForbidden(actor.id)
        if not actor.is_admin:
            self._record_refusal(actor, now, "rol_no_autorizado")
            raise ApproverRoleRequired(actor.id)

    def _record_refusal(self, actor: User, now: datetime, reason: str) -> None:
        self.refused_approval_attempts.append(
            RefusedApprovalAttempt(actor.id, actor.role, now, reason)
        )

    def _ensure_awaiting_decision(self) -> None:
        if self.status not in AWAITING_DECISION:
            raise InvalidTransition(self.status)
