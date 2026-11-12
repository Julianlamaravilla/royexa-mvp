"""The server-rendered pages (CON-02, T7). HTML in Spanish, one cookie session (T6), forms
that carry a one-time token (T7-P4), and a strict content policy: no inline script or style.

This module states what it needs from the container (`WebContainer`) instead of importing
it, so the composition root can import the web without a cycle."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Protocol
from urllib.parse import parse_qs

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from royexa.cash_box.domain import NoOpenCashBox
from royexa.identity_access.domain import InvalidCredentials, SessionRequired, User
from royexa.loans.domain import LoanTerms, exact_decimal
from royexa.sales.domain import DisbursementNotFound, DisbursementStatus
from royexa.shared.money import Money
from royexa.shared.payments import PaymentMethod
from royexa.shared.errors import DomainError
from royexa.web import messages
from royexa.web.forms import ClaimState, Outcome
from royexa.web.format import long_date, money, parse_amount, short_date
from royexa.web.session import SESSION_COOKIE, clear_session_cookie, set_session_cookie

HERE = Path(__file__).parent
MAX_FORM_BYTES = 64 * 1024
CONTENT_POLICY = (
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
    "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
)
LOGIN_PATH = "/web/login"
ROUTE_PATH = "/web/ruta"
ADMIN_PATH = "/web/admin"
CLOSE_PATH = "/web/cierre"
REQUESTS_PATH = "/web/admin/solicitudes"
LEDGER_LIMIT = 200
NEW_DISBURSEMENT_PATH = "/web/desembolso/nuevo"


class WebContainer(Protocol):
    authenticator: object
    form_tokens: object
    visit_queries: object
    queries: object
    client_queries: object
    request: object
    confirm: object
    approve: object
    reject: object
    dispatcher: object
    close_cash_box: object
    cash_close_queries: object
    discrepancy_queries: object
    register_payment: object
    register_non_payment: object
    currency_symbol: str


class LoginRequired(Exception):
    """No valid session: the page leads to the login instead of answering 401."""


def initials(name: str) -> str:
    """Up to two capital letters for the round avatar of a client or a user."""
    return "".join(word[0] for word in name.split()[:2]).upper() or "?"


def _environment(symbol: str) -> Environment:
    environment = Environment(
        loader=FileSystemLoader(HERE / "templates"),
        autoescape=select_autoescape(["html"]),
    )
    environment.filters["money"] = lambda cents: money(cents, symbol)
    environment.filters["short_date"] = short_date
    environment.filters["exact"] = exact_decimal
    environment.filters["initials"] = initials
    return environment


async def read_form(request: Request) -> dict[str, str]:
    """application/x-www-form-urlencoded, first value of each field, capped in size."""
    body = await request.body()
    if len(body) > MAX_FORM_BYTES:
        return {}
    parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
    return {name: values[0] for name, values in parsed.items()}


def _session_token(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise LoginRequired()
    return token


def _redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


async def run_once(
    container: WebContainer,
    request: Request,
    purpose: str,
    action: Callable[[User, dict[str, str]], Outcome],
) -> Response:
    """T7-P4. Runs `action` once for a form token: a repeat of the same form, a double tap or
    a retry of the browser shows the recorded result and repeats nothing. A form whose token
    is missing, unknown or from another session does nothing."""
    session_token = _session_token(request)
    try:
        user = await run_in_threadpool(container.authenticator.authenticate, session_token)
    except SessionRequired:
        raise LoginRequired() from None
    form = await read_form(request)
    token = form.get("ficha", "")
    claim = await run_in_threadpool(container.form_tokens.claim, token, session_token, purpose)
    if claim.state is ClaimState.INVALID:
        return _message(
            container,
            403,
            "Formulario no válido",
            "El formulario venció o no es válido. Ábrelo de nuevo desde la ruta del día.",
            ROUTE_PATH,
            "Volver a la ruta",
        )
    if claim.state is ClaimState.PENDING:
        return _message(
            container,
            409,
            "En proceso",
            "Tu envío anterior todavía se está procesando. Espera unos segundos y revisa la ruta.",
            ROUTE_PATH,
            "Ver la ruta del día",
        )
    if claim.state is ClaimState.FRESH:
        try:
            outcome = await run_in_threadpool(action, user, form)
        except DomainError as error:
            outcome = Outcome("error", messages.describe(error), ROUTE_PATH)
        await run_in_threadpool(container.form_tokens.finish, token, outcome)
    return _redirect(f"/web/resultado/{token}")


def _render(container: WebContainer, name: str, status: int = 200, **context) -> HTMLResponse:
    html = _environment(container.currency_symbol).get_template(name).render(**context)
    return HTMLResponse(html, status_code=status)


def _message(
    container: WebContainer,
    status: int,
    heading: str,
    text: str,
    next_path: str,
    link_text: str,
    kind: str = "error",
) -> HTMLResponse:
    return _render(
        container,
        "mensaje.html",
        status,
        heading=heading,
        text=text,
        next_path=next_path,
        link_text=link_text,
        kind=kind,
    )


def install_web(app: FastAPI, container: WebContainer) -> None:
    router = APIRouter(prefix="/web")

    async def current(request: Request) -> tuple[str, User]:
        token = _session_token(request)
        try:
            return token, await run_in_threadpool(container.authenticator.authenticate, token)
        except SessionRequired:
            raise LoginRequired() from None

    async def home_for(user: User) -> str:
        return ADMIN_PATH if user.is_admin else ROUTE_PATH

    @router.get("/")
    async def index(request: Request) -> Response:
        try:
            _, user = await current(request)
        except LoginRequired:
            return _redirect(LOGIN_PATH)
        return _redirect(await home_for(user))

    @router.get("/login")
    async def login_page() -> Response:
        return _render(container, "login.html", error=None, user_id="")

    @router.post("/login")
    async def login(request: Request) -> Response:
        form = await read_form(request)
        user_id, password = form.get("user_id", ""), form.get("password", "")
        try:
            result = await run_in_threadpool(container.authenticator.login, user_id, password)
        except InvalidCredentials:
            return _render(
                container,
                "login.html",
                401,
                error="Usuario o contraseña incorrectos",
                user_id=user_id,
            )
        response = _redirect(await home_for(result.user))
        lifetime = int(
            (result.expires_at - container.authenticator.clock_now()).total_seconds()
        )
        set_session_cookie(response, result.token, lifetime, request.url.scheme == "https")
        return response

    @router.post("/logout")
    async def logout(request: Request) -> Response:
        session_token = _session_token(request)
        try:
            await run_in_threadpool(container.authenticator.authenticate, session_token)
        except SessionRequired:
            raise LoginRequired() from None
        form = await read_form(request)
        claim = await run_in_threadpool(
            container.form_tokens.claim, form.get("ficha", ""), session_token, "salir"
        )
        if claim.state is ClaimState.INVALID:
            return _message(
                container,
                403,
                "Formulario no válido",
                "El formulario venció o no es válido. Vuelve a abrir la página.",
                ROUTE_PATH,
                "Volver",
            )
        try:
            await run_in_threadpool(container.authenticator.logout, session_token)
        except SessionRequired:
            pass
        response = _redirect(LOGIN_PATH)
        clear_session_cookie(response)
        return response

    @router.get("/ruta")
    async def route_page(request: Request) -> Response:
        token, user = await current(request)
        if user.is_admin:
            return _redirect(ADMIN_PATH)
        panels = await run_in_threadpool(container.visit_queries.panels, user, user.id)
        try:
            box = await run_in_threadpool(container.queries.cash_box, user.id)
        except NoOpenCashBox:
            box = None  # a day without collection has no box (T5a)
        logout_token = await run_in_threadpool(container.form_tokens.issue, token, "salir")
        names = await client_names()
        mine = await run_in_threadpool(container.queries.for_collector, user.id)
        disbursements = [
            {
                "id": item.id,
                "client_name": names.get(item.client_id, item.client_id),
                "terms": item.terms,
                "status_text": messages.status_text(item),
                "status_short": messages.status_short(item),
                "status_kind": messages.status_kind(item),
            }
            for item in mine
        ]
        return _render(
            container,
            "ruta.html",
            close_text=await close_text(user, box),
            disbursements=disbursements,
            user=user,
            day=long_date(panels.day),
            panels=panels,
            box=box,
            logout_token=logout_token,
        )

    async def visit_form(request: Request, loan_id: str, template: str, purpose: str) -> Response:
        """T7b: the form of a client who is still pending on today's route; anyone else gets
        no form, so a closed visit cannot be registered twice from a stale link."""
        token, user = await current(request)
        if user.is_admin:
            return _redirect(ADMIN_PATH)
        panels = await run_in_threadpool(container.visit_queries.panels, user, user.id)
        visit = next((item for item in panels.pending if item.loan_id == loan_id), None)
        if visit is None:
            return _message(
                container, 404, "Sin visita pendiente",
                "Este cliente ya no está pendiente de visita en tu ruta de hoy.",
                ROUTE_PATH, "Volver a la ruta",
            )
        form_token = await run_in_threadpool(container.form_tokens.issue, token, purpose)
        earliest = (panels.day + timedelta(days=1)).isoformat()
        return _render(container, template, visit=visit, token=form_token, earliest=earliest)

    async def client_names() -> dict[str, str]:
        clients = await run_in_threadpool(container.client_queries.all)
        return {client.id: client.name for client in clients}

    async def close_text(user: User, box) -> str | None:
        """The close of today's box, written for the page, once the box is closed."""
        if box is None or not box.closed:
            return None
        found = await run_in_threadpool(container.cash_close_queries.all, user.id, box.day)
        return messages.close_summary(found[0], container.currency_symbol) if found else None

    def device_time(form: dict[str, str]) -> datetime:
        """The device clock when it sent one, the server clock when it did not (no script)."""
        now = container.authenticator.clock_now()
        try:
            claimed = datetime.fromisoformat(form.get("device_time", ""))
        except ValueError:
            return now
        return claimed if claimed.tzinfo else claimed.replace(tzinfo=now.tzinfo)

    @router.get("/pago/{loan_id}")
    async def payment_page(loan_id: str, request: Request) -> Response:
        return await visit_form(request, loan_id, "pago.html", f"pago:{loan_id}")

    @router.post("/pago/{loan_id}")
    async def payment(loan_id: str, request: Request) -> Response:
        back = f"/web/pago/{loan_id}"

        def register(user: User, form: dict[str, str]) -> Outcome:
            cents = parse_amount(form.get("monto", ""))
            if not cents:
                return Outcome(
                    "error", "El importe no es válido. Escríbelo como 1.234,56 y mayor que cero.", back
                )
            try:
                method = PaymentMethod(form.get("medio", ""))
            except ValueError:
                return Outcome("error", "Elige el medio de pago: efectivo o transferencia.", back)
            _, loan = container.register_payment.execute(
                user, loan_id, Money(cents), method, device_time(form)
            )
            symbol = container.currency_symbol
            text = (
                f"Pago de {money(cents, symbol)} registrado. "
                f"Saldo restante {money(loan.outstanding.cents, symbol)}."
            )
            if not loan.outstanding.cents:
                text += " El préstamo quedó liquidado."
            return Outcome("ok", text, ROUTE_PATH)

        return await run_once(container, request, f"pago:{loan_id}", register)

    @router.get("/no-pago/{loan_id}")
    async def non_payment_page(loan_id: str, request: Request) -> Response:
        return await visit_form(request, loan_id, "no_pago.html", f"no-pago:{loan_id}")

    @router.post("/no-pago/{loan_id}")
    async def non_payment(loan_id: str, request: Request) -> Response:
        back = f"/web/no-pago/{loan_id}"

        def register(user: User, form: dict[str, str]) -> Outcome:
            try:
                commitment = date.fromisoformat(form.get("compromiso", ""))
            except ValueError:
                return Outcome("error", "Elige la fecha de compromiso.", back)
            container.register_non_payment.execute(
                user, loan_id, form.get("motivo", ""), commitment, device_time(form)
            )
            return Outcome(
                "ok",
                f"No pago registrado. Compromiso para el {short_date(commitment)}.",
                ROUTE_PATH,
            )

        return await run_once(container, request, f"no-pago:{loan_id}", register)

    def whole_number(text: str) -> int | None:
        return int(text.strip()) if re.fullmatch(r"\s*\d{1,3}\s*", text) else None

    @router.get("/desembolso/nuevo")
    async def new_disbursement_page(request: Request) -> Response:
        token, user = await current(request)
        if user.is_admin:
            return _redirect(ADMIN_PATH)
        panels = await run_in_threadpool(container.visit_queries.panels, user, user.id)
        clients = await run_in_threadpool(container.client_queries.all)
        form_token = await run_in_threadpool(container.form_tokens.issue, token, "desembolso")
        return _render(
            container,
            "desembolso_nuevo.html",
            clients=[c for c in clients if c.route_id == panels.route_id],
            token=form_token,
        )

    @router.post("/desembolso/nuevo")
    async def new_disbursement(request: Request) -> Response:
        def register(user: User, form: dict[str, str]) -> Outcome:
            back = NEW_DISBURSEMENT_PATH
            cents = parse_amount(form.get("monto", ""))
            days = whole_number(form.get("plazo", ""))
            count = whole_number(form.get("cuotas", ""))
            if not cents:
                text = "El importe no es válido. Escríbelo como 1.234,56 y mayor que cero."
            elif days is None:
                text = "El plazo debe ser un número entero de días."
            elif count is None:
                text = "El número de cuotas debe ser un número entero."
            else:
                try:
                    terms = LoanTerms(Money(cents), days, count)
                    asked = container.request.execute(user, form.get("cliente", ""), terms)
                except DomainError as error:
                    return Outcome("error", messages.describe(error), back)
                text = "Solicitud registrada. " + (
                    "Supera tu límite: necesita la autorización de un administrador."
                    if asked.status is DisbursementStatus.PENDING_AUTHORIZATION
                    else "Espera la aprobación del administrador."
                )
                return Outcome("ok", text, f"/web/desembolso/{asked.id}")
            return Outcome("error", text, back)

        return await run_once(container, request, "desembolso", register)

    @router.get("/desembolso/{disbursement_id}")
    async def disbursement_page(disbursement_id: str, request: Request) -> Response:
        token, user = await current(request)
        if user.is_admin:
            return _redirect(ADMIN_PATH)
        try:
            detail = await run_in_threadpool(container.queries.detail, disbursement_id)
        except DisbursementNotFound:
            detail = None
        if detail is None or detail.disbursement.collector_id != user.id:
            return _message(
                container, 404, "Sin solicitud", "No se encontró esa solicitud en tu ruta.",
                ROUTE_PATH, "Volver a la ruta",
            )
        item = detail.disbursement
        form_token = None
        if item.status is DisbursementStatus.APPROVED:
            form_token = await run_in_threadpool(
                container.form_tokens.issue, token, f"codigo:{disbursement_id}"
            )
        names = await client_names()
        return _render(
            container,
            "desembolso.html",
            item=item,
            client_name=names.get(item.client_id, item.client_id),
            status_text=messages.status_text(item),
            token=form_token,
        )

    @router.post("/desembolso/{disbursement_id}/codigo")
    async def confirm_disbursement(disbursement_id: str, request: Request) -> Response:
        back = f"/web/desembolso/{disbursement_id}"

        def confirm(user: User, form: dict[str, str]) -> Outcome:
            code = "".join(form.get("codigo", "").split()).upper()
            try:
                done = container.confirm.execute(user, disbursement_id, code, device_time(form))
            except DomainError as error:
                return Outcome("error", messages.describe(error), back)
            client = container.client_queries.get(done.client_id)
            amount = money(done.terms.principal.cents, container.currency_symbol)
            return Outcome(
                "ok", f"Desembolso confirmado: entregaste {amount} a {client.name}.", ROUTE_PATH
            )

        return await run_once(container, request, f"codigo:{disbursement_id}", confirm)

    @router.get("/cierre")
    async def close_page(request: Request) -> Response:
        token, user = await current(request)
        if user.is_admin:
            return _redirect(ADMIN_PATH)
        panels = await run_in_threadpool(container.visit_queries.panels, user, user.id)
        try:
            box = await run_in_threadpool(container.queries.cash_box, user.id)
        except NoOpenCashBox:
            box = None
        form_token = None
        if box is not None and not box.closed and not panels.pending:
            form_token = await run_in_threadpool(container.form_tokens.issue, token, "cierre")
        return _render(
            container,
            "cierre.html",
            box=box,
            pending=panels.pending,
            token=form_token,
            close_text=await close_text(user, box),
        )

    @router.post("/cierre")
    async def close_box(request: Request) -> Response:
        def close(user: User, form: dict[str, str]) -> Outcome:
            cents = parse_amount(form.get("entregado", ""))
            if cents is None:
                return Outcome(
                    "error", "El importe entregado no es válido. Escríbelo como 1.234,56.", CLOSE_PATH
                )
            try:
                done = container.close_cash_box.execute(
                    user, user.id, Money(cents), device_time(form)
                )
            except DomainError as error:
                return Outcome("error", messages.describe(error), CLOSE_PATH)
            text = "Caja cerrada. " + messages.close_summary(done, container.currency_symbol)
            return Outcome("ok", text, ROUTE_PATH)

        return await run_once(container, request, "cierre", close)

    async def admin_only(request: Request) -> tuple[str, User] | Response:
        """T8: the administrator's pages; anyone else is sent to their own."""
        token, user = await current(request)
        return (token, user) if user.is_admin else _redirect(ROUTE_PATH)

    @router.get("/admin")
    async def admin_page(request: Request) -> Response:
        guard = await admin_only(request)
        if isinstance(guard, Response):
            return guard
        token, user = guard
        logout_token = await run_in_threadpool(container.form_tokens.issue, token, "salir")
        waiting = await run_in_threadpool(container.queries.awaiting_decision)
        return _render(
            container, "admin.html", user=user, logout_token=logout_token, waiting=len(waiting)
        )

    @router.get("/admin/solicitudes")
    async def requests_page(request: Request) -> Response:
        guard = await admin_only(request)
        if isinstance(guard, Response):
            return guard
        token, _ = guard
        names = await client_names()
        rows = []
        for item in await run_in_threadpool(container.queries.awaiting_decision):
            approve, reject = [
                await run_in_threadpool(container.form_tokens.issue, token, f"{verb}:{item.id}")
                for verb in ("aprobar", "rechazar")
            ]
            rows.append(
                {
                    "id": item.id,
                    "client_name": names.get(item.client_id, item.client_id),
                    "collector_id": item.collector_id,
                    "terms": item.terms,
                    "waiting_text": messages.waiting_text(item),
                    "over_limit": item.status is DisbursementStatus.PENDING_AUTHORIZATION,
                    "approve_token": approve,
                    "reject_token": reject,
                }
            )
        return _render(container, "solicitudes.html", rows=rows)

    def decision(verb: str, past: str) -> Callable:
        async def handler(disbursement_id: str, request: Request) -> Response:
            guard = await admin_only(request)
            if isinstance(guard, Response):
                return guard

            def decide(user: User, form: dict[str, str]) -> Outcome:
                try:
                    if verb == "aprobar":
                        container.approve.execute(
                            user, disbursement_id, form.get("motivo", "").strip() or None
                        )
                        container.dispatcher.dispatch()  # the client gets the code now
                    else:
                        container.reject.execute(user, disbursement_id, form.get("motivo", ""))
                except DomainError as error:
                    return Outcome("error", messages.describe(error), REQUESTS_PATH)
                return Outcome("ok", f"Solicitud {past}.", REQUESTS_PATH)

            return await run_once(container, request, f"{verb}:{disbursement_id}", decide)

        return handler

    router.post("/admin/solicitudes/{disbursement_id}/aprobar")(decision("aprobar", "aprobada"))
    router.post("/admin/solicitudes/{disbursement_id}/rechazar")(decision("rechazar", "rechazada"))

    @router.get("/admin/libro")
    async def ledger_page(request: Request) -> Response:
        guard = await admin_only(request)
        if isinstance(guard, Response):
            return guard
        entries = await run_in_threadpool(container.queries.ledger)
        return _render(
            container, "libro.html", entries=list(reversed(entries))[:LEDGER_LIMIT], limit=LEDGER_LIMIT
        )

    @router.get("/admin/clientes")
    async def clients_page(request: Request) -> Response:
        guard = await admin_only(request)
        if isinstance(guard, Response):
            return guard
        return _render(
            container, "clientes.html", clients=await run_in_threadpool(container.client_queries.all)
        )

    @router.get("/admin/descuadres")
    async def discrepancies_page(request: Request) -> Response:
        """T9 (RF-07, CA-13): the same report as the API, for a period chosen in the page."""
        guard = await admin_only(request)
        if isinstance(guard, Response):
            return guard
        asked = request.query_params
        error = report = None
        try:
            since, until = (
                date.fromisoformat(asked[name]) if asked.get(name) else None
                for name in ("desde", "hasta")
            )
            report = await run_in_threadpool(container.discrepancy_queries.report, since, until)
        except ValueError:
            error = "Escribe las fechas del período completas (año, mes y día)."
        except DomainError as problem:
            error = messages.describe(problem)
        return _render(
            container, "descuadres.html", report=report, error=error,
            since=asked.get("desde", ""), until=asked.get("hasta", ""),
        )

    @router.get("/admin/cajas")
    async def closes_page(request: Request) -> Response:
        guard = await admin_only(request)
        if isinstance(guard, Response):
            return guard
        closes = await run_in_threadpool(container.cash_close_queries.all)
        rows = [
            {
                "collector_id": close.collector_id,
                "day": close.day,
                "summary": messages.close_summary(close, container.currency_symbol),
            }
            for close in reversed(closes)
        ]
        return _render(container, "cajas.html", rows=rows)

    @router.get("/resultado/{token}")
    async def result_page(token: str, request: Request) -> Response:
        session_token, _ = await current(request)
        outcome = await run_in_threadpool(container.form_tokens.outcome_of, token, session_token)
        if outcome is None:
            return _message(
                container, 404, "Sin resultado", "No hay un resultado para ese formulario.",
                ROUTE_PATH, "Volver a la ruta",
            )
        return _message(
            container,
            200,
            "Listo" if outcome.kind == "ok" else "No se pudo completar",
            outcome.text,
            outcome.next_path,
            "Continuar",
            kind=outcome.kind,
        )

    @app.exception_handler(LoginRequired)
    async def login_required(_: Request, __: LoginRequired) -> Response:
        return _redirect(LOGIN_PATH)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/web"):
            response.headers["Content-Security-Policy"] = CONTENT_POLICY
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "same-origin"
            if not request.url.path.startswith("/web/static/"):
                response.headers["Cache-Control"] = "no-store"
        return response

    app.mount("/web/static", StaticFiles(directory=HERE / "static"), name="web-static")
    app.include_router(router)
