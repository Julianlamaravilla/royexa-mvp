"""The server-rendered pages (CON-02, T7). HTML in Spanish, one cookie session (T6), forms
that carry a one-time token (T7-P4), and a strict content policy: no inline script or style.

This module states what it needs from the container (`WebContainer`) instead of importing
it, so the composition root can import the web without a cycle."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol
from urllib.parse import parse_qs

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from royexa.identity_access.domain import InvalidCredentials, SessionRequired, User
from royexa.loans.domain import exact_decimal
from royexa.shared.errors import DomainError
from royexa.web import messages
from royexa.web.forms import ClaimState, Outcome
from royexa.web.format import long_date, money, short_date
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


class WebContainer(Protocol):
    authenticator: object
    form_tokens: object
    visit_queries: object
    queries: object
    currency_symbol: str


class LoginRequired(Exception):
    """No valid session: the page leads to the login instead of answering 401."""


def _environment(symbol: str) -> Environment:
    environment = Environment(
        loader=FileSystemLoader(HERE / "templates"),
        autoescape=select_autoescape(["html"]),
    )
    environment.filters["money"] = lambda cents: money(cents, symbol)
    environment.filters["short_date"] = short_date
    environment.filters["exact"] = exact_decimal
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
        box = await run_in_threadpool(container.queries.cash_box, user.id)
        logout_token = await run_in_threadpool(container.form_tokens.issue, token, "salir")
        return _render(
            container,
            "ruta.html",
            user=user,
            day=long_date(panels.day),
            panels=panels,
            box=box,
            logout_token=logout_token,
        )

    @router.get("/admin")
    async def admin_page(request: Request) -> Response:
        token, user = await current(request)
        if not user.is_admin:
            return _redirect(ROUTE_PATH)
        logout_token = await run_in_threadpool(container.form_tokens.issue, token, "salir")
        return _render(container, "admin.html", user=user, logout_token=logout_token)

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
