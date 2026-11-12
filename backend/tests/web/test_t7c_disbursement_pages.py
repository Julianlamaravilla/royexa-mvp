"""T7c: the collector requests a disbursement and validates the code the client dictates.

Runs on both adapters. FakeClock starts on Friday 2026-10-30 at 14:00 UTC and a code lasts
60 minutes. The route of cobrador-1 holds cliente-1 (no loans), cliente-2 (an unpaid loan)
and cliente-3 (a settled loan); cliente-4 belongs to another route. The collector's own
limit is 500.000,00 and the route's 800.000,00.
"""

import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from support import ADMIN, COLLECTOR

from royexa.api import create_app
from royexa.seed import demo_password

NEW_PAGE = "/web/desembolso/nuevo"


def _browser(container, user: str = COLLECTOR) -> TestClient:
    browser = TestClient(create_app(container), follow_redirects=False)
    browser.post("/web/login", data={"user_id": user, "password": demo_password(user)})
    return browser


def _field(html: str, name: str = "ficha") -> str:
    found = re.search(rf'name="{name}" value="([^"]+)"', html)
    assert found, f"no hidden field {name!r}"
    return found.group(1)


def _outcome(browser, response) -> str:
    assert response.status_code == 303, response.text
    return browser.get(response.headers["location"]).text


def _ask(browser, client="cliente-1", amount="1.000,00", days="20", count="20", token=None):
    token = token or _field(browser.get(NEW_PAGE).text)
    return browser.post(
        NEW_PAGE,
        data={"ficha": token, "cliente": client, "monto": amount, "plazo": days, "cuotas": count},
    )


def _ids(browser) -> list[str]:
    """The disbursements the route page links to, newest first."""
    html = browser.get("/web/ruta").text
    return re.findall(r'href="/web/desembolso/(?!nuevo)([^"/]+)"', html)


def _asked(browser, **kwargs) -> str:
    before = _ids(browser)
    _outcome(browser, _ask(browser, **kwargs))
    [new] = [i for i in _ids(browser) if i not in before]
    return new


def _confirm(browser, disbursement_id: str, code: str, token=None):
    path = f"/web/desembolso/{disbursement_id}"
    token = token or _field(browser.get(path).text)
    return browser.post(
        f"{path}/codigo",
        data={"ficha": token, "codigo": code, "device_time": "2026-10-30T14:01:00Z"},
    )


def test_t7c_the_route_offers_the_request_and_lists_no_disbursement_at_first(container):
    html = _browser(container).get("/web/ruta").text

    assert f'href="{NEW_PAGE}"' in html and "Solicitar desembolso" in html
    assert "Desembolsos (0)" in html


def test_t7c_the_request_form_lists_the_clients_of_the_route_with_20_and_20(container):
    html = _browser(container).get(NEW_PAGE).text

    for name in ("Cliente sin prestamos", "Cliente con saldo pendiente", "Cliente con prestamo liquidado"):
        assert name in html
    assert "Cliente de otra ruta" not in html
    assert re.search(r'name="plazo"[^>]*value="20"', html)
    assert re.search(r'name="cuotas"[^>]*value="20"', html)
    assert 'name="monto"' in html and _field(html)
    assert "<script>" not in html and "style=" not in html and "onclick=" not in html


def test_t7c_a_request_is_registered_and_waits_for_the_administrator(flow, container):
    browser = _browser(container)

    page = _outcome(browser, _ask(browser, amount="1.500,50", days="30", count="25"))

    assert "Solicitud registrada" in page
    [disbursement_id] = _ids(browser)
    stored = flow.read(disbursement_id)
    assert stored["status"] == "SOLICITADO" and stored["client_id"] == "cliente-1"
    assert stored["amount_cents"] == 150_050
    assert (stored["term_days"], stored["installment_count"]) == (30, 25)
    assert "Desembolsos (1)" in browser.get("/web/ruta").text
    detail = browser.get(f"/web/desembolso/{disbursement_id}").text
    assert "Esperando la aprobación" in detail and 'name="codigo"' not in detail


def test_t7c_a_double_tap_or_a_resend_requests_once(flow, container):
    browser = _browser(container)
    token = _field(browser.get(NEW_PAGE).text)

    first = _ask(browser, token=token)
    second = _ask(browser, token=token)

    assert first.headers["location"] == second.headers["location"]
    assert len(_ids(browser)) == 1


def test_t7c_above_the_collector_limit_the_request_waits_for_an_authorization(flow, container):
    browser = _browser(container)

    _outcome(browser, _ask(browser, amount="600.000,00"))

    [disbursement_id] = _ids(browser)
    assert flow.read(disbursement_id)["status"] == "EN_ESPERA_AUTORIZACION"
    assert "autorización" in browser.get(f"/web/desembolso/{disbursement_id}").text


def test_t7c_above_the_route_limit_the_request_is_refused_in_spanish(container):
    browser = _browser(container)

    page = _outcome(browser, _ask(browser, amount="900.000,00"))

    assert "límite de la ruta" in page and "No se pudo completar" in page
    assert _ids(browser) == []


def test_t7c_a_client_with_an_unpaid_loan_is_refused_in_spanish(container):
    browser = _browser(container)

    page = _outcome(browser, _ask(browser, client="cliente-2"))

    assert "préstamo anterior sin liquidar" in page
    assert _ids(browser) == []


def test_t7c_a_client_of_another_route_is_refused_in_spanish(container):
    browser = _browser(container)

    page = _outcome(browser, _ask(browser, client="cliente-4"))

    assert "no es de tu ruta" in page
    assert _ids(browser) == []


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"amount": "abc"}, "importe"),
        ({"amount": "0"}, "importe"),
        ({"amount": "1000.50"}, "importe"),
        ({"days": "veinte"}, "plazo"),
        ({"days": ""}, "plazo"),
        ({"count": "0"}, "cuotas"),
        ({"count": "x"}, "cuotas"),
        ({"days": "10", "count": "20"}, "un día de cobro por cuota"),
        ({"client": "no-existe"}, "No se encontró el cliente"),
    ],
)
def test_t7c_invalid_terms_are_refused_in_spanish_and_nothing_is_requested(container, fields, expected):
    browser = _browser(container)

    page = _outcome(browser, _ask(browser, **fields))

    assert expected in page
    assert _ids(browser) == []


def test_t7c_the_names_from_the_database_and_the_page_are_escaped(flow, container):
    flow._post("/v1/clients", ADMIN, {"name": "<b>Peligro</b>", "route_id": "ruta-1"})

    html = _browser(container).get(NEW_PAGE).text

    assert "<b>Peligro</b>" not in html and "&lt;b&gt;Peligro&lt;/b&gt;" in html


def test_t7c_once_approved_the_page_asks_for_the_code_and_a_good_code_pays_the_client(flow, container):
    browser = _browser(container)
    disbursement_id = _asked(browser, amount="1.000,00")
    assert flow.approve(disbursement_id).status_code == 200
    code = flow.issued_code(disbursement_id)
    before = flow.cash_balance()
    page = browser.get(f"/web/desembolso/{disbursement_id}").text
    assert "Aprobado" in page and 'name="codigo"' in page and code not in page

    result = _outcome(browser, _confirm(browser, disbursement_id, code))

    assert "Desembolso confirmado" in result and "1.000,00" in result
    stored = flow.read(disbursement_id)
    assert stored["status"] == "CONFIRMADO" and stored["loan"]["principal_cents"] == 100_000
    assert flow.cash_balance() == before - 100_000
    assert "Confirmado" in browser.get(f"/web/desembolso/{disbursement_id}").text


def test_t7c_the_code_is_accepted_in_lowercase_and_with_spaces(flow, container):
    browser = _browser(container)
    disbursement_id = _asked(browser)
    flow.approve(disbursement_id)
    code = flow.issued_code(disbursement_id)

    typed = f"  {code.lower()} "
    assert "Desembolso confirmado" in _outcome(browser, _confirm(browser, disbursement_id, typed))


def test_t7c_a_wrong_code_moves_no_money_and_the_collector_can_try_again(flow, container):
    browser = _browser(container)
    disbursement_id = _asked(browser)
    flow.approve(disbursement_id)
    code = flow.issued_code(disbursement_id)
    before = flow.cash_balance()

    page = _outcome(browser, _confirm(browser, disbursement_id, "ZZZZ"))

    assert "código no es correcto" in page
    assert f'href="/web/desembolso/{disbursement_id}"' in page
    assert flow.read(disbursement_id)["status"] == "APROBADO" and flow.cash_balance() == before
    assert "Desembolso confirmado" in _outcome(browser, _confirm(browser, disbursement_id, code))


def test_t7c_a_double_tap_on_the_code_confirms_once(flow, container):
    browser = _browser(container)
    disbursement_id = _asked(browser)
    flow.approve(disbursement_id)
    code = flow.issued_code(disbursement_id)
    before = flow.cash_balance()
    token = _field(browser.get(f"/web/desembolso/{disbursement_id}").text)

    for _ in range(3):
        _confirm(browser, disbursement_id, code, token=token)

    assert flow.cash_balance() == before - 100_000
    assert len(flow.ledger(disbursement_id)) == 1


def test_t7c_an_expired_code_leaves_its_entry_and_says_so(flow, container, clock):
    browser = _browser(container)
    disbursement_id = _asked(browser)
    flow.approve(disbursement_id)
    code = flow.issued_code(disbursement_id)
    before = flow.cash_balance()
    clock.advance(timedelta(minutes=61))

    page = _outcome(browser, _confirm(browser, disbursement_id, code))

    assert "caducó" in page and "quedó registrado" in page
    [entry] = flow.ledger(disbursement_id)
    assert entry["reason"] == "codigo_caducado"
    assert flow.read(disbursement_id)["status"] == "CADUCADO" and flow.cash_balance() == before
    assert "caducó" in browser.get(f"/web/desembolso/{disbursement_id}").text


def test_t7c_a_rejected_request_shows_the_reason(flow, container):
    browser = _browser(container)
    disbursement_id = _asked(browser)
    flow.reject(disbursement_id, reason="monto muy alto para el cliente")

    detail = browser.get(f"/web/desembolso/{disbursement_id}").text

    assert "Rechazado" in detail and "monto muy alto para el cliente" in detail
    assert 'name="codigo"' not in detail


def test_t7c_a_closed_box_refuses_the_confirmation_in_spanish(flow, container):
    browser = _browser(container)
    disbursement_id = _asked(browser)
    flow.approve(disbursement_id)
    code = flow.issued_code(disbursement_id)
    token = _field(browser.get(f"/web/desembolso/{disbursement_id}").text)
    flow.visit_everyone()
    assert flow.close_box(flow.cash_balance()).status_code == 201

    page = _outcome(browser, _confirm(browser, disbursement_id, code, token=token))

    assert "caja del día ya está cerrada" in page
    assert flow.read(disbursement_id)["status"] == "APROBADO"


def test_t7c_the_route_lists_what_is_in_progress_with_its_state(flow, container, clock):
    browser = _browser(container)
    first = _asked(browser, client="cliente-1")
    clock.advance(timedelta(minutes=1))
    second = _asked(browser, client="cliente-3", amount="200,00")
    flow.approve(second)

    html = browser.get("/web/ruta").text

    assert "Desembolsos (2)" in html
    assert f'href="/web/desembolso/{first}"' in html and f'href="/web/desembolso/{second}"' in html
    assert "Esperando la aprobación" in html and "Aprobado" in html
    assert html.index(second) < html.index(first), "newest first"


def test_t7c_another_collector_and_the_administrator_do_not_see_the_disbursement(flow, container):
    disbursement_id = _asked(_browser(container))
    flow.approve(disbursement_id)

    other = _browser(container, "cobrador-2")
    assert other.get(f"/web/desembolso/{disbursement_id}").status_code == 404
    assert _ids(other) == []
    assert _browser(container, ADMIN).get(f"/web/desembolso/{disbursement_id}").headers["location"] == "/web/admin"
    assert _browser(container, ADMIN).get(NEW_PAGE).headers["location"] == "/web/admin"
    assert other.get("/web/desembolso/no-existe").status_code == 404


def test_t7c_a_token_of_one_form_does_not_serve_another(flow, container):
    browser = _browser(container)
    disbursement_id = _asked(browser)
    flow.approve(disbursement_id)
    code = flow.issued_code(disbursement_id)
    request_token = _field(browser.get(NEW_PAGE).text)

    stolen = _confirm(browser, disbursement_id, code, token=request_token)
    forged = browser.post(NEW_PAGE, data={"cliente": "cliente-1", "monto": "1,00", "plazo": "20", "cuotas": "20"})

    assert stolen.status_code == 403 and forged.status_code == 403
    assert flow.read(disbursement_id)["status"] == "APROBADO"
    assert len(_ids(browser)) == 1


@pytest.mark.parametrize("path", [NEW_PAGE, "/web/desembolso/algo"])
def test_t7c_without_a_session_the_pages_lead_to_the_login(container, path):
    anonymous = TestClient(create_app(container), follow_redirects=False)

    if path == NEW_PAGE:
        assert anonymous.post(path, data={"ficha": "x"}).headers["location"] == "/web/login"
    assert anonymous.get(path).headers["location"] == "/web/login"
    assert anonymous.post(path + "/codigo", data={"ficha": "x"}).headers["location"] == "/web/login"
