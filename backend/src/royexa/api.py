"""HTTP entry (CON-03). Resolves the actor, checks the role, and hands over to use cases.

The actor is the user of a valid session (T6): a token from POST /v1/auth/login, sent as
`Authorization: Bearer` or, for the server-rendered pages, in an HttpOnly cookie. Users are
still seeded (ALT-06B). Errors follow RFC 9457 problem details.
"""

from datetime import date, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from royexa.bootstrap import Container
from royexa.cash_box.domain import (
    AdjustmentNotAllowed,
    CashBox,
    CashBoxClosed,
    CashCloseNotAllowed,
    CashClose,
    NoOpenCashBox,
    PendingVisitsRemain,
)
from royexa.clients.domain import (
    Client,
    ClientNotFound,
    ClientRegistrationNotAllowed,
    InvalidClient,
)
from royexa.web.routes import install_web
from royexa.web.session import SESSION_COOKIE, clear_session_cookie, set_session_cookie
from royexa.identity_access.domain import (
    CurrentPasswordIncorrect,
    InvalidCredentials,
    RouteNotFound,
    SessionRequired,
    UnknownActor,
    User,
    WeakPassword,
)
from royexa.ledger.domain import InvalidLedgerEntry, LedgerEntry, LedgerEntryNotFound
from royexa.loans.application import DayPanels, PendingVisit
from royexa.loans.domain import (
    ExceptionNotAllowed,
    InvalidCommitmentDate,
    InvalidLoanTerms,
    Loan,
    LoanAlreadySettled,
    LoanNotFound,
    LoanTerms,
    NonPayment,
    Payment,
    PaymentExceedsBalance,
    PaymentNotAllowed,
    PriorLoanNotSettled,
    ReasonRequired,
    VisitNotAllowed,
    exact_decimal,
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
from royexa.shared.payments import PaymentMethod

PROBLEM_BASE = "https://royexa.local/problemas/"
PROBLEM_MEDIA_TYPE = "application/problem+json"


class AdminRoleRequired(DomainError):
    """ALT-06B: the role check that belongs to the entry."""


_PROBLEMS: dict[type[DomainError], tuple[int, str, str]] = {
    UnknownActor: (401, "actor-desconocido", "Actor desconocido"),
    InvalidCredentials: (401, "credenciales-invalidas", "Usuario o contrasena incorrectos"),
    SessionRequired: (401, "sesion-requerida", "Se requiere una sesion valida"),
    CurrentPasswordIncorrect: (
        403,
        "contrasena-actual-incorrecta",
        "La contrasena actual es incorrecta",
    ),
    WeakPassword: (422, "contrasena-debil", "La contrasena nueva no cumple la politica"),
    AdminRoleRequired: (403, "rol-administrador-requerido", "Se requiere rol de administrador"),
    SelfApprovalForbidden: (403, "autoaprobacion-prohibida", "Quien origina no puede aprobar"),
    ApproverRoleRequired: (403, "rol-aprobador-requerido", "Solo un administrador aprueba"),
    DeciderRoleRequired: (403, "rol-aprobador-requerido", "Solo un administrador rechaza"),
    ValidatorNotAllowed: (403, "validador-no-autorizado", "Solo el cobrador de la ruta valida"),
    ClientOutsideRoute: (403, "cliente-fuera-de-ruta", "El cliente no pertenece a la ruta"),
    ClientRegistrationNotAllowed: (403, "rol-administrador-requerido", "Solo un administrador da de alta clientes"),
    AdjustmentNotAllowed: (403, "rol-administrador-requerido", "Solo un administrador registra un ajuste"),
    CashCloseNotAllowed: (403, "cierre-no-permitido", "Solo el cobrador de la caja la cierra"),
    VisitNotAllowed: (403, "visita-no-permitida", "Solo el cobrador de la ruta registra la visita"),
    PaymentNotAllowed: (403, "pago-no-permitido", "Solo el cobrador de la ruta registra el pago"),
    ExceptionNotAllowed: (403, "excepcion-no-permitida", "Excepcion no permitida"),
    DisbursementNotFound: (404, "desembolso-no-encontrado", "Desembolso no encontrado"),
    LedgerEntryNotFound: (404, "asiento-no-encontrado", "Asiento no encontrado"),
    ClientNotFound: (404, "cliente-no-encontrado", "Cliente no encontrado"),
    LoanNotFound: (404, "prestamo-no-encontrado", "Prestamo no encontrado"),
    RouteNotFound: (404, "ruta-no-encontrada", "Ruta no encontrada"),
    NoOpenCashBox: (409, "caja-no-disponible", "El cobrador no tiene caja abierta"),
    PendingVisitsRemain: (409, "visitas-pendientes", "Existen visitas pendientes"),
    CashBoxClosed: (409, "caja-cerrada", "La caja esta cerrada"),
    LoanAlreadySettled: (409, "prestamo-liquidado", "El prestamo ya esta liquidado"),
    PriorLoanNotSettled: (409, "prestamo-anterior-sin-liquidar", "Prestamo anterior sin liquidar"),
    InvalidTransition: (409, "transicion-invalida", "Transicion de estado no permitida"),
    ConfirmationCodeExpired: (409, "codigo-caducado", "El codigo de confirmacion caduco"),
    WriteConflict: (409, "conflicto-de-escritura", "Operacion concurrente; reintente"),
    InvalidConfirmationCode: (422, "codigo-invalido", "Codigo de confirmacion invalido"),
    AmountExceedsRouteLimit: (422, "monto-sobre-limite-de-ruta", "Monto sobre el limite de ruta"),
    InvalidCommitmentDate: (422, "compromiso-invalido", "El compromiso debe ser posterior al dia del registro"),
    PaymentExceedsBalance: (422, "pago-excede-saldo", "El pago excede el saldo del prestamo"),
    InvalidLedgerEntry: (422, "asiento-invalido", "Asiento invalido"),
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
        headers={"WWW-Authenticate": "Bearer"} if slug == "sesion-requerida" else None,
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
    paid_cents: int


class PaymentBody(BaseModel):
    amount_cents: int = Field(gt=0)
    method: PaymentMethod
    device_time: datetime


class NonPaymentBody(BaseModel):
    reason: str
    commitment_date: date
    device_time: datetime


class NonPaymentOut(BaseModel):
    id: str
    loan_id: str
    client_id: str
    collector_id: str
    reason: str
    commitment_date: date
    device_time: datetime
    server_time: datetime


class PendingVisitOut(BaseModel):
    client_id: str
    client_name: str
    loan_id: str
    outstanding_cents: int
    remaining_installments: str


class LoginBody(BaseModel):
    user_id: str
    password: str


class PasswordBody(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(max_length=1024)


class LoginOut(BaseModel):
    token: str
    token_type: str
    user_id: str
    role: str
    expires_at: datetime


class CloseBody(BaseModel):
    delivered_cents: int = Field(ge=0)
    device_time: datetime


class CashCloseOut(BaseModel):
    id: str
    cash_box_id: str
    collector_id: str
    day: date
    expected_cents: int
    delivered_cents: int
    discrepancy_cents: int
    closed_by: str
    device_time: datetime
    server_time: datetime


class PaidClientOut(BaseModel):
    client_id: str
    client_name: str
    cash_cents: int
    transfer_cents: int
    payments: int


class UnpaidClientOut(BaseModel):
    client_id: str
    client_name: str
    loan_id: str
    reason: str
    commitment_date: date


class PanelTotalsOut(BaseModel):
    cash_cents: int
    transfer_cents: int


class PanelsOut(BaseModel):
    day: date
    collector_id: str
    route_id: str
    pending: list[PendingVisitOut]
    paid: list[PaidClientOut]
    unpaid: list[UnpaidClientOut]
    totals: PanelTotalsOut


class AllocationOut(BaseModel):
    sequence: int
    amount_cents: int


class PaymentOut(BaseModel):
    id: str
    loan_id: str
    client_id: str
    collector_id: str
    amount_cents: int
    method: str
    device_time: datetime
    server_time: datetime
    allocations: list[AllocationOut]


class LoanOut(BaseModel):
    id: str
    client_id: str
    status: str
    principal_cents: int
    interest_cents: int
    outstanding_cents: int
    installment_count: int
    remaining_installments: str
    installments: list[InstallmentOut]


class PaymentResultOut(BaseModel):
    payment: PaymentOut
    loan: LoanOut


class AdjustmentBody(BaseModel):
    amount_cents: int
    reason: str
    device_time: datetime


class LedgerEntryOut(BaseModel):
    id: str
    disbursement_id: str | None
    payment_id: str | None
    payment_method: str | None
    adjusts_entry_id: str | None
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
    day: date
    opening_balance_cents: int
    balance_cents: int
    closed: bool


class NoticeOut(BaseModel):
    """Deliberately omits the payload: the code never leaves through this API (RN-03)."""

    id: str
    kind: str
    client_id: str
    disbursement_id: str | None
    payment_id: str | None
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
        client_id=loan.client_id,
        status="LIQUIDADO" if loan.is_settled else "ACTIVO",
        principal_cents=loan.principal.cents,
        interest_cents=loan.interest.cents,
        outstanding_cents=loan.outstanding.cents,
        installment_count=loan.installment_count,
        remaining_installments=exact_decimal(loan.remaining_installments),
        installments=[
            InstallmentOut(
                sequence=item.sequence,
                due_date=item.due_date.isoformat(),
                amount_cents=item.amount.cents,
                paid_cents=item.paid.cents,
            )
            for item in loan.installments
        ],
    )


def _payment_out(payment: Payment) -> PaymentOut:
    return PaymentOut(
        id=payment.id,
        loan_id=payment.loan_id,
        client_id=payment.client_id,
        collector_id=payment.collector_id,
        amount_cents=payment.amount.cents,
        method=payment.method.value,
        device_time=payment.device_time,
        server_time=payment.server_time,
        allocations=[
            AllocationOut(sequence=item.sequence, amount_cents=item.amount.cents)
            for item in payment.allocations
        ],
    )


def _non_payment_out(item: NonPayment) -> NonPaymentOut:
    return NonPaymentOut(
        id=item.id,
        loan_id=item.loan_id,
        client_id=item.client_id,
        collector_id=item.collector_id,
        reason=item.reason,
        commitment_date=item.commitment_date,
        device_time=item.device_time,
        server_time=item.server_time,
    )


def _pending_out(item: PendingVisit) -> PendingVisitOut:
    return PendingVisitOut(
        client_id=item.client_id,
        client_name=item.client_name,
        loan_id=item.loan_id,
        outstanding_cents=item.outstanding.cents,
        remaining_installments=exact_decimal(item.remaining_installments),
    )


def _close_out(close: CashClose) -> CashCloseOut:
    return CashCloseOut(
        id=close.id,
        cash_box_id=close.cash_box_id,
        collector_id=close.collector_id,
        day=close.day,
        expected_cents=close.expected.cents,
        delivered_cents=close.delivered.cents,
        discrepancy_cents=close.discrepancy.cents,
        closed_by=close.closed_by,
        device_time=close.device_time,
        server_time=close.server_time,
    )


def _panels_out(panels: DayPanels) -> PanelsOut:
    return PanelsOut(
        day=panels.day,
        collector_id=panels.collector_id,
        route_id=panels.route_id,
        pending=[_pending_out(item) for item in panels.pending],
        paid=[
            PaidClientOut(
                client_id=item.client_id,
                client_name=item.client_name,
                cash_cents=item.cash.cents,
                transfer_cents=item.transfer.cents,
                payments=item.payments,
            )
            for item in panels.paid
        ],
        unpaid=[
            UnpaidClientOut(
                client_id=item.client_id,
                client_name=item.client_name,
                loan_id=item.loan_id,
                reason=item.reason,
                commitment_date=item.commitment_date,
            )
            for item in panels.unpaid
        ],
        totals=PanelTotalsOut(
            cash_cents=panels.cash_total.cents, transfer_cents=panels.transfer_total.cents
        ),
    )


def _entry_out(entry: LedgerEntry) -> LedgerEntryOut:
    return LedgerEntryOut(
        id=entry.id,
        disbursement_id=entry.disbursement_id,
        payment_id=entry.payment_id,
        payment_method=entry.payment_method,
        adjusts_entry_id=entry.adjusts_entry_id,
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
        payment_id=message.payment_id,
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
        day=box.day,
        opening_balance_cents=box.opening_balance.cents,
        balance_cents=box.balance.cents,
        closed=box.closed,
    )


def _client_out(client: Client) -> ClientOut:
    return ClientOut(id=client.id, name=client.name, route_id=client.route_id)


def create_app(container: Container) -> FastAPI:
    app = FastAPI(title="ROYEXA API", version="0.3.0")

    def session_token(request: Request) -> str:
        """T6-P1: the Authorization header wins and is never mixed with the cookie, so a
        bad token is refused instead of silently falling back to a cookie."""
        header = request.headers.get("authorization")
        if header is not None:
            scheme, _, token = header.partition(" ")
            if scheme.lower() != "bearer" or not token.strip():
                raise SessionRequired("malformed Authorization header")
            return token.strip()
        cookie = request.cookies.get(SESSION_COOKIE)
        if not cookie:
            raise SessionRequired("no session")
        return cookie

    Token = Annotated[str, Depends(session_token)]

    def current_actor(token: Token) -> User:
        return container.authenticator.authenticate(token)

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

    @app.post("/v1/auth/login", response_model=LoginOut)
    def login(body: LoginBody, request: Request, response: Response) -> LoginOut:
        result = container.authenticator.login(body.user_id, body.password)
        lifetime = int((result.expires_at - container.authenticator.clock_now()).total_seconds())
        set_session_cookie(response, result.token, lifetime, request.url.scheme == "https")
        return LoginOut(
            token=result.token,
            token_type="Bearer",
            user_id=result.user.id,
            role=result.user.role.value,
            expires_at=result.expires_at,
        )

    @app.post("/v1/auth/password", status_code=204)
    def change_password(body: PasswordBody, token: Token) -> Response:
        container.authenticator.change_password(token, body.current_password, body.new_password)
        return Response(status_code=204)

    @app.post("/v1/auth/logout", status_code=204)
    def logout(token: Token, request: Request) -> Response:
        container.authenticator.logout(token)
        reply = Response(status_code=204)
        clear_session_cookie(reply)
        return reply

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
    def read_cash_box(
        collector_id: str, _: Actor, day: Annotated[date | None, Query(alias="date")] = None
    ) -> CashBoxOut:
        return _box_out(container.queries.cash_box(collector_id, day))

    @app.post("/v1/clients", status_code=201, response_model=ClientOut)
    def register_client(body: ClientBody, actor: Actor) -> ClientOut:
        return _client_out(container.register_client.execute(actor, body.name, body.route_id))

    @app.get("/v1/clients", response_model=list[ClientOut])
    def list_clients(_: Actor) -> list[ClientOut]:
        return [_client_out(client) for client in container.client_queries.all()]

    @app.get("/v1/clients/{client_id}", response_model=ClientOut)
    def read_client(client_id: str, _: Actor) -> ClientOut:
        return _client_out(container.client_queries.get(client_id))

    @app.get("/v1/clients/{client_id}/loans", response_model=list[LoanOut])
    def read_client_loans(client_id: str, _: Actor) -> list[LoanOut]:
        return [_loan_out(loan) for loan in container.loan_queries.for_client(client_id)]

    @app.post("/v1/loans/{loan_id}/payments", status_code=201, response_model=PaymentResultOut)
    def register_payment(loan_id: str, body: PaymentBody, actor: Actor) -> PaymentResultOut:
        payment, loan = container.register_payment.execute(
            actor, loan_id, Money(body.amount_cents), body.method, body.device_time
        )
        return PaymentResultOut(payment=_payment_out(payment), loan=_loan_out(loan))

    @app.get("/v1/loans/{loan_id}/payments", response_model=list[PaymentOut])
    def read_payments(loan_id: str, _: Actor) -> list[PaymentOut]:
        return [_payment_out(item) for item in container.payment_queries.for_loan(loan_id)]

    @app.post("/v1/loans/{loan_id}/non-payments", status_code=201, response_model=NonPaymentOut)
    def register_non_payment(loan_id: str, body: NonPaymentBody, actor: Actor) -> NonPaymentOut:
        return _non_payment_out(
            container.register_non_payment.execute(
                actor, loan_id, body.reason, body.commitment_date, body.device_time
            )
        )

    @app.get("/v1/loans/{loan_id}/non-payments", response_model=list[NonPaymentOut])
    def read_non_payments(loan_id: str, _: Actor) -> list[NonPaymentOut]:
        return [_non_payment_out(item) for item in container.visit_queries.non_payments_of(loan_id)]

    @app.get("/v1/routes/{route_id}/pending-visits", response_model=list[PendingVisitOut])
    def read_pending_visits(
        route_id: str, actor: Actor, day: Annotated[date | None, Query(alias="date")] = None
    ) -> list[PendingVisitOut]:
        return [_pending_out(item) for item in container.visit_queries.pending(actor, route_id, day)]

    @app.get("/v1/loans/{loan_id}", response_model=LoanOut)
    def read_loan(loan_id: str, _: Actor) -> LoanOut:
        return _loan_out(container.loan_queries.get(loan_id))

    @app.post(
        "/v1/ledger/{entry_id}/adjustments", status_code=201, response_model=LedgerEntryOut
    )
    def register_adjustment(entry_id: str, body: AdjustmentBody, actor: Actor) -> LedgerEntryOut:
        return _entry_out(
            container.register_adjustment.execute(
                actor, entry_id, Money(body.amount_cents), body.reason, body.device_time
            )
        )

    @app.get("/v1/cash-boxes/{collector_id}/panels", response_model=PanelsOut)
    def read_panels(collector_id: str, actor: Actor) -> PanelsOut:
        return _panels_out(container.visit_queries.panels(actor, collector_id))

    @app.post(
        "/v1/cash-boxes/{collector_id}/close", status_code=201, response_model=CashCloseOut
    )
    def close_cash_box(collector_id: str, body: CloseBody, actor: Actor) -> CashCloseOut:
        return _close_out(
            container.close_cash_box.execute(
                actor, collector_id, Money(body.delivered_cents), body.device_time
            )
        )

    @app.get("/v1/cash-closes", response_model=list[CashCloseOut])
    def read_cash_closes(
        _: Admin,
        collector_id: str | None = None,
        day: Annotated[date | None, Query(alias="date")] = None,
    ) -> list[CashCloseOut]:
        return [_close_out(c) for c in container.cash_close_queries.all(collector_id, day)]

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
    def read_notifications(
        _: Admin, disbursement_id: str | None = None, payment_id: str | None = None
    ) -> list[NoticeOut]:
        return [
            _notice_out(message) for message in container.notices.list(disbursement_id, payment_id)
        ]

    install_web(app, container)
    return app
