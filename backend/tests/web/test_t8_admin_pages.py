"""T8: the administrator decides disbursements from the web and reads the ledger, the clients
and the closed boxes. Runs on both adapters. FakeClock starts on Friday 2026-10-30.
"""

import re

import pytest
from fastapi.testclient import TestClient
from support import ADMIN, COLLECTOR, OTHER_ADMIN

from royexa.api import create_app
from royexa.seed import demo_password

PAGES = ["/web/admin/solicitudes", "/web/admin/libro", "/web/admin/clientes", "/web/admin/cajas"]


def _browser(container, user: str = ADMIN) -> TestClient:
    browser = TestClient(create_app(container), follow_redirects=False)
    browser.post("/web/login", data={"user_id": user, "password": demo_password(user)})
    return browser


def _tokens(html: str) -> list[str]:
    return re.findall(r'name="ficha" value="([^"]+)"', html)


def _decide(browser, disbursement_id: str, verb: str, reason: str | None = None):
    html = browser.get("/web/admin/solicitudes").text
    form = re.search(
        rf'action="/web/admin/solicitudes/{disbursement_id}/{verb}".*?</form>', html, re.S
    )
    assert form, f"no {verb} form for {disbursement_id}"
    data = {"ficha": _tokens(form.group(0))[0]}
    if reason is not None:
        data["motivo"] = reason
    return browser.post(f"/web/admin/solicitudes/{disbursement_id}/{verb}", data=data)


def _outcome(browser, response) -> str:
    assert response.status_code == 303, response.text
    return browser.get(response.headers["location"]).text


def test_t8_the_admin_home_links_to_every_page_and_counts_what_waits(flow, container):
    flow.requested()
    html = _browser(container).get("/web/admin").text

    for path in PAGES:
        assert f'href="{path}"' in html, path
    assert "Solicitudes en espera (1)" in html


@pytest.mark.parametrize("path", PAGES)
def test_t8_the_pages_are_for_the_administrator_only(container, path):
    assert _browser(container, COLLECTOR).get(path).headers["location"] == "/web/ruta"
    anonymous = TestClient(create_app(container), follow_redirects=False)
    assert anonymous.get(path).headers["location"] == "/web/login"


def test_t8_the_waiting_requests_show_who_what_and_how_much(flow, container):
    flow.requested(client="cliente-1", amount_cents=150_050)
    flow.requested(client="cliente-3", amount_cents=60_000_000)

    html = _browser(container).get("/web/admin/solicitudes").text

    assert "Cliente sin prestamos" in html and "1.500,50" in html and "cobrador-1" in html
    assert "Esperando la autorización" in html and "600.000,00" in html
    assert html.count("Aprobar") >= 2 and html.count("Rechazar") >= 2
    assert "<script>" not in html and "style=" not in html and "onclick=" not in html


def test_t8_with_nothing_waiting_the_page_says_so(container):
    assert "No hay solicitudes en espera" in _browser(container).get("/web/admin/solicitudes").text


def test_t8_approving_issues_the_code_and_sends_it_to_the_client(flow, container):
    disbursement = flow.requested()
    browser = _browser(container)

    page = _outcome(browser, _decide(browser, disbursement["id"], "aprobar"))

    assert "Solicitud aprobada" in page
    stored = flow.read(disbursement["id"])
    assert stored["status"] == "APROBADO" and stored["approved_by"] == ADMIN
    code = [s.payload["code"] for s in flow.notifier.delivered if "code" in s.payload]
    assert len(code) == 1, "the web sends the code without a second step"
    assert flow.confirm(disbursement["id"], code[0]).status_code == 200
    assert "No hay solicitudes en espera" in browser.get("/web/admin/solicitudes").text


def test_t8_a_double_tap_approves_once(flow, container):
    disbursement = flow.requested()
    browser = _browser(container)
    html = browser.get("/web/admin/solicitudes").text
    token = _tokens(re.search(r"aprobar\".*?</form>", html, re.S).group(0))[0]
    path = f"/web/admin/solicitudes/{disbursement['id']}/aprobar"

    for _ in range(3):
        browser.post(path, data={"ficha": token})

    assert len([s for s in flow.notifier.delivered if "code" in s.payload]) == 1
    assert len(flow.notices(disbursement["id"])) == 1


def test_t8_nobody_approves_what_they_requested_and_the_attempt_stays_on_record(flow, container):
    disbursement = flow.requested(actor=ADMIN)
    browser = _browser(container)

    page = _outcome(browser, _decide(browser, disbursement["id"], "aprobar"))

    assert "originaste" in page and "No se pudo completar" in page
    stored = flow.read(disbursement["id"])
    assert stored["status"] == "SOLICITADO" and len(stored["rejected_approval_attempts"]) == 1
    other = _browser(container, OTHER_ADMIN)
    assert "Solicitud aprobada" in _outcome(other, _decide(other, disbursement["id"], "aprobar"))


def test_t8_rejecting_states_its_reason_and_the_collector_sees_it(flow, container):
    disbursement = flow.requested()
    browser = _browser(container)

    page = _outcome(browser, _decide(browser, disbursement["id"], "rechazar", "monto muy alto"))

    assert "Solicitud rechazada" in page
    stored = flow.read(disbursement["id"])
    assert stored["status"] == "RECHAZADO" and stored["decision_reason"] == "monto muy alto"
    collector = _browser(container, COLLECTOR)
    assert "monto muy alto" in collector.get(f"/web/desembolso/{disbursement['id']}").text


@pytest.mark.parametrize("reason", ["", "   "])
def test_t8_rejecting_without_a_reason_is_refused_in_spanish(flow, container, reason):
    disbursement = flow.requested()
    browser = _browser(container)

    page = _outcome(browser, _decide(browser, disbursement["id"], "rechazar", reason))

    assert "motivo" in page and flow.read(disbursement["id"])["status"] == "SOLICITADO"


def test_t8_a_stale_form_on_a_decided_request_is_refused_in_spanish(flow, container):
    disbursement = flow.requested()
    browser = _browser(container)
    html = browser.get("/web/admin/solicitudes").text
    token = _tokens(re.search(r"rechazar\".*?</form>", html, re.S).group(0))[0]
    assert flow.approve(disbursement["id"], OTHER_ADMIN).status_code == 200

    response = browser.post(
        f"/web/admin/solicitudes/{disbursement['id']}/rechazar", data={"ficha": token, "motivo": "tarde"}
    )

    assert "no está en un estado" in _outcome(browser, response)
    assert flow.read(disbursement["id"])["status"] == "APROBADO"


def test_t8_a_collector_cannot_decide_even_with_a_form_of_the_administrator(flow, container):
    disbursement = flow.requested()
    admin, collector = _browser(container), _browser(container, COLLECTOR)
    html = admin.get("/web/admin/solicitudes").text
    token = _tokens(re.search(r"aprobar\".*?</form>", html, re.S).group(0))[0]
    path = f"/web/admin/solicitudes/{disbursement['id']}/aprobar"

    assert collector.post(path, data={"ficha": token}).headers["location"] == "/web/ruta"
    assert flow.read(disbursement["id"])["status"] == "SOLICITADO"
    assert admin.post(path, data={}).status_code == 403


def test_t8_the_ledger_lists_every_entry_newest_first(flow, container, clock):
    flow.confirmed()
    flow.pay("prestamo-impago", 30_000, "TRANSFERENCIA")

    html = _browser(container).get("/web/admin/libro").text

    assert "DESEMBOLSO" in html and "1.000,00" in html
    assert "PAGO" in html and "300,00" in html and "TRANSFERENCIA" in html
    assert "cobrador-1" in html and "caja-cobrador-1-2026-10-30" in html


def test_t8_the_ledger_shows_an_expired_attempt_with_its_reason(flow, container, clock):
    from datetime import timedelta

    disbursement = flow.approved()
    code = flow.issued_code(disbursement["id"])
    clock.advance(timedelta(minutes=61))
    flow.confirm(disbursement["id"], code)

    html = _browser(container).get("/web/admin/libro").text

    assert "codigo_caducado" in html


def test_t8_the_clients_page_lists_clients_with_their_route_and_escapes_names(flow, container):
    flow._post("/v1/clients", ADMIN, {"name": "<b>Nuevo</b>", "route_id": "ruta-2"})

    html = _browser(container).get("/web/admin/clientes").text

    for name in ("Cliente sin prestamos", "Cliente de otra ruta"):
        assert name in html
    assert "ruta-1" in html and "ruta-2" in html
    assert "<b>Nuevo</b>" not in html and "&lt;b&gt;Nuevo&lt;/b&gt;" in html


def test_t8_the_closed_boxes_page_shows_each_close_with_its_discrepancy(flow, container):
    browser = _browser(container)
    assert "Todavía no hay cajas cerradas" in browser.get("/web/admin/cajas").text
    flow.pay("prestamo-impago", 70_000)
    assert flow.close_box(65_050).status_code == 201

    html = browser.get("/web/admin/cajas").text

    assert "cobrador-1" in html and "30/10/2026" in html
    assert "Esperado 700,00" in html and "Entregado 650,50" in html and "Faltan 49,50" in html
