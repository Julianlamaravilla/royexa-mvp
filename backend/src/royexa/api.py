"""HTTP entry (CON-03). Resolves the actor, checks the role, and hands over to use cases.

Identity comes from the X-Actor-Id header against seeded users: declared limitation of
ALT-06B. Errors follow RFC 9457 problem details.
"""

from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from royexa.bootstrap import Container
from royexa.cash_box.domain import CashBox, CashBoxClosed, NoOpenCashBox
from royexa.clients.domain import (
    Client,
    ClientNotFound,
    ClientRegistrationNotAllowed,
    InvalidClient,
)
from royexa.identity_access.domain import RouteNotFound, UnknownActor, User
from royexa.ledger.domain import LedgerEntry
from royexa.loans.domain import (
    ExceptionNotAllowed,
    InvalidLoanTerms,
    Loan,
    LoanTerms,
    PriorLoanNotSettled,
    ReasonRequired,
)
from royexa.sales.application import DisbursementDetail
from royexa.sales.domain import (
    AmountExceedsRouteLimit,
    ApproverRoleRequired,
    ClientOutsideRoute,
    ConfirmationCodeExpired,
    DeciderRoleRequired,
    DisbursementNotFound,
    InvalidConfirmationCode,
    InvalidTransition,
    SelfApprovalForbidden,
    ValidatorNotAllowed,
)
from royexa.shared.errors import DomainError, WriteConflict
from royexa.shared.money import InvalidAmount, Money
from royexa.shared.outbox import OutboxMessage

PROBLEM_BASE = "https://royexa.local/problemas/"
PROBLEM_MEDIA_TYPE = "application/problem+json"


class AdminRoleRequired(DomainError):
    """ALT-06B: the role check that belongs to the entry."""


_PROBLEMS: dict[type[DomainError], tuple[int, str, str]] = {
    UnknownActor: (401, "actor-desconocido", "Actor desconocido"),
    AdminRoleRequired: (403, "rol-administrador-requerido", "Se requiere rol de administrador"),
    SelfApprovalForbidden: (403, "autoaprobacion-prohibida", "Quien origina no puede aprobar"),
    ApproverRoleRequired: (403, "rol-aprobador-requerido", "Solo un administrador aprueba"),
    DeciderRoleRequired: (403, "rol-aprobador-requerido", "Solo un administrador rechaza"),
    ValidatorNotAllowed: (403, "validador-no-autorizado", "Solo el cobrador de la ruta valida"),
    ClientOutsideRoute: (403, "cliente-fuera-de-ruta", "El cliente no pertenece a la ruta"),
    ClientRegistrationNotAllowed: (403, "rol-administrador-requerido", "Solo un administrador da de alta clientes"),
    ExceptionNotAllowed: (403, "excepcion-no-permitida", "Excepcion no permitida"),
    DisbursementNotFound: (404, "desembolso-no-encontrado", "Desembolso no encontrado"),
    ClientNotFound: (404, "cliente-no-encontrado", "Cliente no encontrado"),
    RouteNotFound: (404, "ruta-no-encontrada", "Ruta no encontrada"),
    NoOpenCashBox: (409, "caja-no-disponible", "El cobrador no tiene caja abierta"),
    CashBoxClosed: (409, "caja-cerrada", "La caja esta cerrada"),
    PriorLoanNotSettled: (409, "prestamo-anterior-sin-liquidar", "Prestamo anterior sin liquidar"),
    InvalidTransition: (409, "transicion-invalida", "Transicion de estado no permitida"),
    ConfirmationCodeExpired: (409, "codigo-caducado", "El codigo de confirmacion caduco"),
    WriteConflict: (409, "conflicto-de-escritura", "Operacion concurrente; reintente"),
    InvalidConfirmationCode: (422, "codigo-invalido", "Codigo de confirmacion invalido"),
    AmountExceedsRouteLimit: (422, "monto-sobre-limite-de-ruta", "Monto sobre el limite de ruta"),
    InvalidClient: (422, "cliente-invalido", "Cliente invalido"),
    InvalidLoanTerms: (422, "condiciones-invalidas", "Condiciones de prestamo invalidas"),
    InvalidAmount: (422, "monto-invalido", "Monto invalido"),
    ReasonRequired: (422, "motivo-requerido", "Se requiere un motivo"),
}


def _problem(status: int, slug: str, title: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type=PROBLEM_MEDIA_TYPE,
        content={"type": PROBLEM_BASE + slug, "title": title, "status": status, "detail": detail},
    )


class RequestBody(BaseModel):
    client_id: str
    amount_cents: int = Field(gt=0)
    term_days: int = Field(gt=0)
    installment_count: int = Field(gt=0)


class DecisionBody(BaseModel):
    reason: str | None = None


class ConfirmBody(BaseModel):
    code: str
    device_time: datetime


class ClientBody(BaseModel):
    name: str
    route_id: str


class ClientOut(BaseModel):
    id: str
    name: str
    route_id: str


class ExceptionBody(BaseModel):
    reason: str


class InstallmentOut(BaseModel):
    sequence: int
    due_date: str
    amount_cents: int


class LoanOut(BaseModel):
    id: str
    principal_cents: int
    interest_cents: int
    outstanding_cents: int
    installments: list[InstallmentOut]


class LedgerEntryOut(BaseModel):
    id: str
    disbursement_id: str
    entry_type: str
    amount_cents: int
    cash_effect_cents: int
    cash_box_id: str
    actor_id: str
    device_time: datetime
    server_time: datetime
    reason: str | None


class AttemptOut(BaseModel):
    actor_id: str
    actor_role: str
    at: datetime
    reason: str


class DisbursementOut(BaseModel):
    id: str
    status: str
    client_id: str
    collector_id: str
    requested_by: str
    requested_at: datetime
    amount_cents: int
    interest_cents: int
    term_days: int
    installment_count: int
    approved_by: str | None
    decided_by: str | None
    decided_at: datetime | None
    decision_reason: str | None
    code_expires_at: datetime | None
    confirmed_by: str | None
    resolved_at: datetime | None
    renewal_exception_id: str | None
    rejected_approval_attempts: list[AttemptOut]
    loan: LoanOut | None
    ledger_entries: list[LedgerEntryOut]


class CashBoxOut(BaseModel):
    id: str
    collector_id: str
    opening_balance_cents: int
    balance_cents: int
    closed: bool


class NoticeOut(BaseModel):
    """Deliberately omits the payload: the code never leaves through this API (RN-03)."""

    id: str
    kind: str
    client_id: str
    disbursement_id: str
    status: str
    attempts: int
    last_error: str | None
    created_at: datetime
    sent_at: datetime | None


class DispatchOut(BaseModel):
    attempted: int
    sent: int


class RenewalExceptionOut(BaseModel):
    id: str
    client_id: str
    prior_loan_id: str
    granted_by: str
    reason: str
    granted_at: datetime


def _loan_out(loan: Loan) -> LoanOut:
    return LoanOut(
        id=loan.id,
        principal_cents=loan.principal.cents,
        interest_cents=loan.interest.cents,
        outstanding_cents=loan.outstanding.cents,
        installments=[
            InstallmentOut(
                sequence=item.sequence,
                due_date=item.due_date.isoformat(),
                amount_cents=item.amount.cents,
            )
            for item in loan.installments
        ],
    )


def _entry_out(entry: LedgerEntry) -> LedgerEntryOut:
    return LedgerEntryOut(
        id=entry.id,
        disbursement_id=entry.disbursement_id,
        entry_type=entry.entry_type.value,
        amount_cents=entry.amount.cents,
        cash_effect_cents=entry.cash_effect.cents,
        cash_box_id=entry.cash_box_id,
        actor_id=entry.actor_id,
        device_time=entry.device_time,
        server_time=entry.server_time,
        reason=entry.reason,
    )


def _disbursement_out(detail: DisbursementDetail) -> DisbursementOut:
    item = detail.disbursement
    return DisbursementOut(
        id=item.id,
        status=item.status.value,
        client_id=item.client_id,
        collector_id=item.collector_id,
        requested_by=item.requested_by,
        requested_at=item.requested_at,
        amount_cents=item.terms.principal.cents,
        interest_cents=item.interest.cents,
        term_days=item.terms.term_days,
        installment_count=item.terms.installment_count,
        approved_by=item.approved_by,
        decided_by=item.decided_by,
        decided_at=item.decided_at,
        decision_reason=item.decision_reason,
        code_expires_at=item.code.expires_at if item.code else None,
        confirmed_by=item.confirmed_by,
        resolved_at=item.resolved_at,
        renewal_exception_id=item.renewal_exception_id,
        rejected_approval_attempts=[
            AttemptOut(
                actor_id=attempt.actor_id,
                actor_role=attempt.actor_role.value,
                at=attempt.at,
                reason=attempt.reason,
            )
            for attempt in item.refused_approval_attempts
        ],
        loan=_loan_out(detail.loan) if detail.loan else None,
        ledger_entries=[_entry_out(entry) for entry in detail.entries],
    )


def _notice_out(message: OutboxMessage) -> NoticeOut:
    return NoticeOut(
        id=message.id,
        kind=message.kind.value,
        client_id=message.client_id,
        disbursement_id=message.disbursement_id,
        status=message.status.value,
        attempts=message.attempts,
        last_error=message.last_error,
        created_at=message.created_at,
        sent_at=message.sent_at,
    )


def _box_out(box: CashBox) -> CashBoxOut:
    return CashBoxOut(
        id=box.id,
        collector_id=box.collector_id,
        opening_balance_cents=box.opening_balance.cents,
        balance_cents=box.balance.cents,
        closed=box.closed,
    )


def _client_out(client: Client) -> ClientOut:
    return ClientOut(id=client.id, name=client.name, route_id=client.route_id)


def create_app(container: Container) -> FastAPI:
    app = FastAPI(title="ROYEXA API", version="0.3.0")

    def current_actor(x_actor_id: Annotated[str, Header()]) -> User:
        return container.directory.user(x_actor_id)

    def current_admin(actor: Annotated[User, Depends(current_actor)]) -> User:
        if not actor.is_admin:
            raise AdminRoleRequired(actor.id)
        return actor

    Actor = Annotated[User, Depends(current_actor)]
    Admin = Annotated[User, Depends(current_admin)]

    @app.exception_handler(DomainError)
    def domain_error(_: Request, error: DomainError) -> JSONResponse:
        for kind in type(error).__mro__:
            if kind in _PROBLEMS:
                status, slug, title = _PROBLEMS[kind]
                return _problem(status, slug, title, str(error))
        return _problem(400, "regla-de-negocio", "Regla de negocio incumplida", str(error))

    @app.exception_handler(RequestValidationError)
    def invalid_request(_: Request, error: RequestValidationError) -> JSONResponse:
        fields = ", ".join(".".join(str(part) for part in item["loc"]) for item in error.errors())
        return _problem(422, "solicitud-invalida", "Solicitud invalida", fields)

    def detail(disbursement_id: str) -> DisbursementOut:
        return _disbursement_out(container.queries.detail(disbursement_id))

    @app.post("/v1/disbursements", status_code=201, response_model=DisbursementOut)
    def request_disbursement(body: RequestBody, actor: Actor) -> DisbursementOut:
        terms = LoanTerms(Money(body.amount_cents), body.term_days, body.installment_count)
        return detail(container.request.execute(actor, body.client_id, terms).id)

    @app.post("/v1/disbursements/{disbursement_id}/approve", response_model=DisbursementOut)
    def approve_disbursement(
        disbursement_id: str, body: DecisionBody, actor: Actor
    ) -> DisbursementOut:
        # The aggregate checks the role here so a refused attempt is recorded (RN-06, EV-11).
        container.approve.execute(actor, disbursement_id, body.reason)
        return detail(disbursement_id)

    @app.post("/v1/disbursements/{disbursement_id}/reject", response_model=DisbursementOut)
    def reject_disbursement(
        disbursement_id: str, body: DecisionBody, actor: Admin
    ) -> DisbursementOut:
        container.reject.execute(actor, disbursement_id, body.reason or "")
        return detail(disbursement_id)

    @app.post("/v1/disbursements/{disbursement_id}/confirm", response_model=DisbursementOut)
    def confirm_disbursement(
        disbursement_id: str, body: ConfirmBody, actor: Actor
    ) -> DisbursementOut:
        container.confirm.execute(actor, disbursement_id, body.code, body.device_time)
        return detail(disbursement_id)

    @app.get("/v1/disbursements/{disbursement_id}", response_model=DisbursementOut)
    def read_disbursement(disbursement_id: str, _: Actor) -> DisbursementOut:
        return detail(disbursement_id)

    @app.get("/v1/ledger", response_model=list[LedgerEntryOut])
    def read_ledger(_: Admin, disbursement_id: str | None = None) -> list[LedgerEntryOut]:
        return [_entry_out(entry) for entry in container.queries.ledger(disbursement_id)]

    @app.get("/v1/cash-boxes/{collector_id}", response_model=CashBoxOut)
    def read_cash_box(collector_id: str, _: Actor) -> CashBoxOut:
        return _box_out(container.queries.cash_box(collector_id))

    @app.post("/v1/clients", status_code=201, response_model=ClientOut)
    def register_client(body: ClientBody, actor: Actor) -> ClientOut:
        return _client_out(container.register_client.execute(actor, body.name, body.route_id))

    @app.get("/v1/clients", response_model=list[ClientOut])
    def list_clients(_: Actor) -> list[ClientOut]:
        return [_client_out(client) for client in container.client_queries.all()]

    @app.get("/v1/clients/{client_id}", response_model=ClientOut)
    def read_client(client_id: str, _: Actor) -> ClientOut:
        return _client_out(container.client_queries.get(client_id))

    @app.post(
        "/v1/clients/{client_id}/renewal-exceptions",
        status_code=201,
        response_model=RenewalExceptionOut,
    )
    def grant_renewal_exception(
        client_id: str, body: ExceptionBody, actor: Actor
    ) -> RenewalExceptionOut:
        exception = container.grant_exception.execute(actor, client_id, body.reason)
        return RenewalExceptionOut(
            id=exception.id,
            client_id=exception.client_id,
            prior_loan_id=exception.prior_loan_id,
            granted_by=exception.granted_by,
            reason=exception.reason,
            granted_at=exception.granted_at,
        )

    @app.post("/v1/notifications/dispatch", response_model=DispatchOut)
    def dispatch_notifications(_: Admin) -> DispatchOut:
        report = container.dispatcher.dispatch()
        return DispatchOut(attempted=report.attempted, sent=report.sent)

    @app.get("/v1/notifications", response_model=list[NoticeOut])
    def read_notifications(_: Admin, disbursement_id: str | None = None) -> list[NoticeOut]:
        return [_notice_out(message) for message in container.notices.list(disbursement_id)]

    return app
