"""T7a: the login page, the day's route, the security headers and the one-time forms of the
server-rendered web. Runs on both adapters except the configuration cases.

FakeClock starts on Friday 2026-10-30 at 14:00 UTC; the route of cobrador-1 holds
cliente-2 (a balance of 700,00 over 7/12 of an installment).
"""

import re
from datetime import timedelta

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from support import ADMIN, COLLECTOR, FakeClock

from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.bootstrap import Settings, build_container
from royexa.seed import demo_password
from royexa.web.forms import Outcome
from royexa.web.routes import run_once


def _browser(container) -> TestClient:
    """A client that keeps cookies and does not follow redirects."""
    return TestClient(create_app(container), follow_redirects=False)


def _login(browser, user: str = COLLECTOR, password: str | None = None):
    return browser.post(
        "/web/login",
        data={"user_id": user, "password": password or demo_password(user)},
    )


def _field(html: str, name: str = "ficha") -> str:
    found = re.search(rf'name="{name}" value="([^"]+)"', html)
    assert found, f"no hidden field {name!r}"
    return found.group(1)


def test_t7a_the_login_page_is_spanish_and_made_for_a_phone(container):
    response = _browser(container).get("/web/login")

    assert response.status_code == 200
    html = response.text
    assert '<html lang="es">' in html
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in html
    assert 'name="user_id"' in html and 'name="password"' in html and 'type="password"' in html
    assert "Ingresar" in html


def test_t7a_every_page_carries_the_security_headers(container):
    response = _browser(container).get("/web/login")

    policy = response.headers["content-security-policy"]
    for directive in ("default-src 'none'", "script-src 'self'", "style-src 'self'",
                      "form-action 'self'", "frame-ancestors 'none'", "base-uri 'none'"):
        assert directive in policy, directive
    assert "unsafe-inline" not in policy
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "same-origin"
    assert response.headers["cache-control"] == "no-store"


def test_t7a_the_pages_have_no_inline_script_or_style_that_the_policy_would_block(container):
    browser = _browser(container)
    _login(browser)

    for path in ("/web/login", "/web/ruta"):
        html = browser.get(path).text
        assert "<script>" not in html and "style=" not in html and "onclick=" not in html, path
        assert '<link rel="stylesheet" href="/web/static/app.css">' in html, path


def test_t7a_the_assets_come_from_the_same_origin(container):
    browser = _browser(container)

    css = browser.get("/web/static/app.css")
    js = browser.get("/web/static/app.js")

    assert css.status_code == 200 and css.headers["content-type"].startswith("text/css")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]
    assert browser.get("/web/static/no-existe.css").status_code == 404


def test_t7a_a_good_login_opens_the_route_with_an_http_only_cookie(container):
    browser = _browser(container)

    response = _login(browser)

    assert response.status_code == 303
    assert response.headers["location"] == "/web/ruta"
    cookie = response.headers["set-cookie"].lower()
    assert "royexa_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    assert browser.get("/web/ruta").status_code == 200


def test_t7a_a_bad_login_says_the_same_for_a_wrong_password_and_an_unknown_user(container):
    browser = _browser(container)

    wrong = _login(browser, COLLECTOR, "esta-no-es-la-clave")
    unknown = _login(browser, "nadie", "esta-no-es-la-clave")

    assert wrong.status_code == unknown.status_code == 401
    assert "Usuario o contraseña incorrectos" in wrong.text

    def without_the_typed_user(html: str) -> str:
        return re.sub(r'name="user_id" value="[^"]*"', 'name="user_id" value=""', html)

    assert without_the_typed_user(wrong.text) == without_the_typed_user(unknown.text)
    assert "set-cookie" not in wrong.headers


def test_t7a_the_login_page_does_not_echo_the_password_and_escapes_the_user(container):
    browser = _browser(container)

    response = _login(browser, '"><script>alert(1)</script>', "mi-clave-secreta-1234")

    assert "mi-clave-secreta-1234" not in response.text
    assert "<script>alert(1)</script>" not in response.text


@pytest.mark.parametrize("path", ["/web/ruta", "/web/admin", "/web/resultado/abc"])
def test_t7a_without_a_session_the_pages_lead_to_the_login(container, path):
    response = _browser(container).get(path)

    assert response.status_code == 303
    assert response.headers["location"] == "/web/login"


def test_t7a_the_root_leads_to_the_route_or_to_the_login(container):
    browser = _browser(container)
    assert browser.get("/web/").headers["location"] == "/web/login"

    _login(browser)

    assert browser.get("/web/").headers["location"] == "/web/ruta"


def test_t7a_an_expired_session_leads_back_to_the_login(container, clock):
    browser = _browser(container)
    _login(browser)
    clock.advance(timedelta(hours=12, seconds=1))

    assert browser.get("/web/ruta").headers["location"] == "/web/login"


def test_t7a_the_route_shows_the_day_the_box_and_who_is_pending(container):
    browser = _browser(container)
    _login(browser)

    html = browser.get("/web/ruta").text

    assert "Ruta del día" in html and "viernes 30 de octubre de 2026" in html
    assert "Cobrador uno" in html
    assert "Caja abierta" in html and "1.000.000,00" in html
    assert "Pendientes (1)" in html
    assert "Cliente con saldo pendiente" in html
    assert "700,00" in html and "7/12" in html
    assert "Pagaron (0)" in html and "No pagaron (0)" in html


def test_t7a_the_route_follows_payments_and_non_payments(flow, container):
    flow.pay("prestamo-impago", 30_000, "EFECTIVO")
    browser = _browser(container)
    _login(browser)

    html = browser.get("/web/ruta").text

    assert "Pendientes (0)" in html
    assert "Pagaron (1)" in html and "Cliente con saldo pendiente" in html
    assert "300,00" in html, "the cash collected, in the Spanish style"


def test_t7a_a_non_payment_moves_the_client_to_the_other_panel(flow, container):
    flow.non_pay("prestamo-impago", "no tiene dinero", "2026-11-02")
    browser = _browser(container)
    _login(browser)

    html = browser.get("/web/ruta").text

    assert "No pagaron (1)" in html and "no tiene dinero" in html
    assert "02/11/2026" in html


def test_t7a_what_comes_from_the_database_is_escaped(flow, container):
    flow._post("/v1/clients", ADMIN, {"name": "<script>alert(1)</script>", "route_id": "ruta-1"})
    created = next(c for c in flow._get("/v1/clients").json() if "script" in c["name"])
    flow.confirmed(client=created["id"])
    browser = _browser(container)
    _login(browser)

    html = browser.get("/web/ruta").text

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_t7a_an_administrator_has_no_route_and_lands_on_their_own_page(container):
    browser = _browser(container)

    assert _login(browser, ADMIN).headers["location"] == "/web/admin"
    assert browser.get("/web/ruta").headers["location"] == "/web/admin"
    assert "Administrador uno" in browser.get("/web/admin").text


def test_t7a_logout_with_its_token_ends_the_session_and_clears_the_cookie(container):
    browser = _browser(container)
    _login(browser)
    token = _field(browser.get("/web/ruta").text)

    response = browser.post("/web/logout", data={"ficha": token})

    assert response.status_code == 303 and response.headers["location"] == "/web/login"
    assert "max-age=0" in response.headers["set-cookie"].lower()
    assert browser.get("/web/ruta").headers["location"] == "/web/login"


@pytest.mark.parametrize("data", [{}, {"ficha": ""}, {"ficha": "inventada"}])
def test_t7a_logout_without_a_valid_token_is_refused_and_changes_nothing(container, data):
    browser = _browser(container)
    _login(browser)

    response = browser.post("/web/logout", data=data)

    assert response.status_code == 403
    assert "formulario" in response.text.lower()
    assert browser.get("/web/ruta").status_code == 200, "still logged in"


def test_t7a_a_token_of_another_session_does_not_log_this_one_out(container):
    victim, attacker = _browser(container), _browser(container)
    _login(victim)
    _login(attacker, ADMIN)
    stolen = _field(attacker.get("/web/admin").text)

    response = victim.post("/web/logout", data={"ficha": stolen})

    assert response.status_code == 403
    assert victim.get("/web/ruta").status_code == 200


def test_t7a_a_form_posted_without_the_cookie_cannot_act(container):
    browser = _browser(container)
    _login(browser)
    token = _field(browser.get("/web/ruta").text)

    anonymous = _browser(container).post("/web/logout", data={"ficha": token})

    assert anonymous.status_code == 303 and anonymous.headers["location"] == "/web/login"
    assert browser.get("/web/ruta").status_code == 200


def test_t7a_run_once_does_the_work_once_and_a_repeat_shows_the_recorded_result(container):
    effects: list[str] = []
    app = create_app(container)

    @app.post("/web/_probe")
    async def probe(request: Request):
        return await run_once(
            container,
            request,
            "sonda",
            lambda user, form: effects.append(user.id) or Outcome("ok", "Hecho", "/web/ruta"),
        )

    browser = TestClient(app, follow_redirects=False)
    _login(browser)
    token = container.form_tokens.issue(browser.cookies["royexa_session"], "sonda")

    first = browser.post("/web/_probe", data={"ficha": token})
    second = browser.post("/web/_probe", data={"ficha": token})

    assert effects == [COLLECTOR], "one effect for two submissions"
    assert first.status_code == second.status_code == 303
    assert first.headers["location"] == second.headers["location"] == f"/web/resultado/{token}"
    page = browser.get(first.headers["location"])
    assert page.status_code == 200 and "Hecho" in page.text


def test_t7a_run_once_records_a_failure_and_still_does_not_repeat_it(container):
    calls: list[int] = []
    app = create_app(container)

    @app.post("/web/_probe")
    async def probe(request: Request):
        def refuse(user, form):
            calls.append(1)
            return Outcome("error", "El pago excede el saldo", "/web/ruta")

        return await run_once(container, request, "sonda", refuse)

    browser = TestClient(app, follow_redirects=False)
    _login(browser)
    token = container.form_tokens.issue(browser.cookies["royexa_session"], "sonda")

    browser.post("/web/_probe", data={"ficha": token})
    again = browser.post("/web/_probe", data={"ficha": token})

    assert calls == [1]
    assert "El pago excede el saldo" in browser.get(again.headers["location"]).text


def test_t7a_the_result_page_is_for_the_session_that_made_the_request(container):
    app = create_app(container)

    @app.post("/web/_probe")
    async def probe(request: Request):
        return await run_once(
            container, request, "sonda", lambda user, form: Outcome("ok", "Reservado", "/web/ruta")
        )

    mine, other = TestClient(app, follow_redirects=False), TestClient(app, follow_redirects=False)
    _login(mine)
    _login(other, ADMIN)
    token = container.form_tokens.issue(mine.cookies["royexa_session"], "sonda")
    mine.post("/web/_probe", data={"ficha": token})

    assert "Reservado" in mine.get(f"/web/resultado/{token}").text
    assert other.get(f"/web/resultado/{token}").status_code == 404


def test_t7a_a_configured_currency_symbol_shows_on_every_amount():
    container = build_container(Settings(currency_symbol="$"), FakeClock(), SimulatedNotifier())
    browser = _browser(container)
    _login(browser)

    html = browser.get("/web/ruta").text

    assert "$ 1.000.000,00" in html and "$ 700,00" in html


def test_t7a_on_sunday_the_route_page_says_there_is_no_collection(container, clock):
    browser = _browser(container)
    clock.advance(timedelta(days=2))  # Sunday 1 November
    _login(browser)

    response = browser.get("/web/ruta")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "domingo 1 de noviembre de 2026" in response.text
    assert "no es día de cobranza" in response.text
    assert "Caja abierta" not in response.text
