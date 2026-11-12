"""T7b: the collector registers a payment and a non-payment from the day's route.

Runs on both adapters. FakeClock starts on Friday 2026-10-30; the route of cobrador-1 holds
cliente-2 with the loan `prestamo-impago` (a balance of 700,00, 7/12 of an installment).
"""

import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from support import ADMIN, COLLECTOR, FakeClock

from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.bootstrap import Settings, build_container
from royexa.seed import demo_password

LOAN = "prestamo-impago"
PAYMENT_PAGE = f"/web/pago/{LOAN}"
NON_PAYMENT_PAGE = f"/web/no-pago/{LOAN}"


def _browser(container, user: str = COLLECTOR) -> TestClient:
    browser = TestClient(create_app(container), follow_redirects=False)
    browser.post("/web/login", data={"user_id": user, "password": demo_password(user)})
    return browser


def _field(html: str, name: str = "ficha") -> str:
    found = re.search(rf'name="{name}" value="([^"]+)"', html)
    assert found, f"no hidden field {name!r}"
    return found.group(1)


def _pay(browser, amount: str, method: str = "EFECTIVO", path: str = PAYMENT_PAGE, token=None):
    token = token or _field(browser.get(path).text)
    return browser.post(
        path,
        data={"ficha": token, "monto": amount, "medio": method, "device_time": "2026-10-30T13:59:00Z"},
    )


def _not_pay(browser, reason: str, day: str, path: str = NON_PAYMENT_PAGE, token=None):
    token = token or _field(browser.get(path).text)
    return browser.post(
        path,
        data={"ficha": token, "motivo": reason, "compromiso": day, "device_time": "2026-10-30T13:59:00Z"},
    )


def _outcome(browser, response) -> str:
    assert response.status_code == 303, response.text
    return browser.get(response.headers["location"]).text


def _payments(flow) -> list[dict]:
    return flow._get(f"/v1/loans/{LOAN}/payments").json()


def test_t7b_each_pending_client_of_the_route_offers_both_registrations(container):
    html = _browser(container).get("/web/ruta").text

    assert f'href="{PAYMENT_PAGE}"' in html and "Registrar pago" in html
    assert f'href="{NON_PAYMENT_PAGE}"' in html and "No pagó" in html


def test_t7b_the_payment_page_shows_the_client_the_balance_and_a_fresh_token(container):
    html = _browser(container).get(PAYMENT_PAGE).text

    assert "Cliente con saldo pendiente" in html
    assert "Saldo 700,00" in html
    assert 'name="monto"' in html and 'name="medio"' in html and 'name="device_time"' in html
    assert 'value="EFECTIVO"' in html and 'value="TRANSFERENCIA"' in html
    assert _field(html)
    assert "<script>" not in html and "style=" not in html and "onclick=" not in html


def test_t7b_a_cash_payment_is_registered_and_reaches_the_box_and_the_route(flow, container):
    browser = _browser(container)
    before = flow.cash_balance()

    response = _pay(browser, "250,00")

    page = _outcome(browser, response)
    assert "Pago de 250,00 registrado" in page and "Saldo restante 450,00" in page
    [payment] = _payments(flow)
    assert payment["amount_cents"] == 25_000 and payment["method"] == "EFECTIVO"
    assert payment["collector_id"] == COLLECTOR
    assert flow.cash_balance() == before + 25_000
    route = browser.get("/web/ruta").text
    assert "Pendientes (0)" in route and "Pagaron (1)" in route


def test_t7b_a_transfer_is_registered_but_does_not_move_the_box(flow, container):
    browser = _browser(container)
    before = flow.cash_balance()

    page = _outcome(browser, _pay(browser, "100,50", "TRANSFERENCIA"))

    assert "Pago de 100,50 registrado" in page
    assert _payments(flow)[0]["method"] == "TRANSFERENCIA"
    assert flow.cash_balance() == before


@pytest.mark.parametrize(
    ("typed", "cents"), [("1,5", 150), (" 2 ", 200), ("1,05", 105), ("600", 60_000), ("0,01", 1)]
)
def test_t7b_the_amount_is_read_in_the_spanish_style(flow, container, typed, cents):
    browser = _browser(container)

    _outcome(browser, _pay(browser, typed))

    assert [p["amount_cents"] for p in _payments(flow)] == [cents]


def test_t7b_a_double_tap_or_a_resend_registers_one_payment(flow, container):
    browser = _browser(container)
    before = flow.cash_balance()
    token = _field(browser.get(PAYMENT_PAGE).text)

    first = _pay(browser, "250,00", token=token)
    second = _pay(browser, "250,00", token=token)
    third = _pay(browser, "250,00", token=token)

    assert len(_payments(flow)) == 1
    assert first.headers["location"] == second.headers["location"] == third.headers["location"]
    assert "Pago de 250,00 registrado" in _outcome(browser, third)
    assert flow.cash_balance() == before + 25_000


def test_t7b_a_payment_above_the_balance_is_refused_in_spanish_and_records_nothing(flow, container):
    browser = _browser(container)

    page = _outcome(browser, _pay(browser, "700,01"))

    assert "mayor que el saldo" in page and "No se pudo completar" in page
    assert _payments(flow) == []
    assert "Pendientes (1)" in browser.get("/web/ruta").text


@pytest.mark.parametrize("amount", ["", "abc", "0", "0,00", "-5", "250.50", "1,234", "1.2.3", "10,5,1"])
def test_t7b_an_amount_that_is_not_clear_is_refused_and_the_link_leads_back_to_the_form(
    flow, container, amount
):
    browser = _browser(container)

    response = _pay(browser, amount)

    page = _outcome(browser, response)
    assert "importe" in page.lower()
    assert f'href="{PAYMENT_PAGE}"' in page
    assert _payments(flow) == []


def test_t7b_an_unknown_payment_method_is_refused(flow, container):
    browser = _browser(container)

    page = _outcome(browser, _pay(browser, "10,00", "CHEQUE"))

    assert "medio de pago" in page.lower()
    assert _payments(flow) == []


def test_t7b_a_closed_box_refuses_the_payment_in_spanish(flow, container):
    browser = _browser(container)
    token = _field(browser.get(PAYMENT_PAGE).text)
    assert flow.non_pay(LOAN).status_code == 201
    assert flow.close_box(flow.cash_balance()).status_code == 201

    page = _outcome(browser, _pay(browser, "10,00", token=token))

    assert "caja del día ya está cerrada" in page
    assert _payments(flow) == []


def test_t7b_a_settled_loan_is_refused_in_spanish(flow, container):
    browser = _browser(container)
    token = _field(browser.get(PAYMENT_PAGE).text)
    assert flow.pay(LOAN, 70_000).status_code == 201

    page = _outcome(browser, _pay(browser, "10,00", token=token))

    assert "No se pudo completar" in page
    assert len(_payments(flow)) == 1


def test_t7b_a_client_who_is_not_pending_has_no_form(container):
    browser = _browser(container)

    for path in ("/web/pago/prestamo-liquidado", "/web/pago/no-existe", "/web/no-pago/no-existe"):
        response = browser.get(path)
        assert response.status_code == 404, path
        assert "ya no está pendiente" in response.text and 'name="ficha"' not in response.text


def test_t7b_after_the_payment_the_form_is_no_longer_offered(flow, container):
    browser = _browser(container)
    _pay(browser, "700,00")

    assert browser.get(PAYMENT_PAGE).status_code == 404


def test_t7b_a_collector_of_another_route_cannot_register_for_this_client(flow, container):
    browser = _browser(container, "cobrador-2")
    mine = _browser(container)
    token = _field(mine.get(PAYMENT_PAGE).text)

    assert browser.get(PAYMENT_PAGE).status_code == 404
    forged = _pay(browser, "10,00", token=token)
    assert forged.status_code == 403, "a token of another session is not accepted"
    assert _payments(flow) == []


def test_t7b_an_administrator_has_no_route_and_is_sent_to_their_page(container):
    browser = _browser(container, ADMIN)

    for path in (PAYMENT_PAGE, NON_PAYMENT_PAGE):
        assert browser.get(path).headers["location"] == "/web/admin"


@pytest.mark.parametrize("path", [PAYMENT_PAGE, NON_PAYMENT_PAGE])
def test_t7b_without_a_session_the_forms_lead_to_the_login(container, path):
    anonymous = TestClient(create_app(container), follow_redirects=False)

    assert anonymous.get(path).headers["location"] == "/web/login"
    assert anonymous.post(path, data={"ficha": "x"}).headers["location"] == "/web/login"


def test_t7b_a_payment_token_serves_neither_another_form_nor_another_loan(flow, container):
    browser = _browser(container)
    token = _field(browser.get(PAYMENT_PAGE).text)

    wrong_form = _not_pay(browser, "motivo", "2026-11-02", token=token)
    wrong_loan = _pay(browser, "10,00", path="/web/pago/prestamo-liquidado", token=token)

    assert wrong_form.status_code == 403 and wrong_loan.status_code == 403
    assert _payments(flow) == []
    assert flow._get(f"/v1/loans/{LOAN}/non-payments").json() == []


def test_t7b_a_forged_or_missing_token_does_nothing(flow, container):
    browser = _browser(container)

    for data in ({}, {"ficha": "inventada", "monto": "10,00", "medio": "EFECTIVO"}):
        assert browser.post(PAYMENT_PAGE, data=data).status_code == 403

    assert _payments(flow) == []


def test_t7b_the_non_payment_page_shows_the_client_and_asks_for_a_date_after_today(container):
    html = _browser(container).get(NON_PAYMENT_PAGE).text

    assert "Cliente con saldo pendiente" in html
    assert 'name="motivo"' in html and 'name="compromiso"' in html and 'type="date"' in html
    assert 'min="2026-10-31"' in html
    assert _field(html)


def test_t7b_a_non_payment_is_registered_and_moves_the_client_on_the_route(flow, container):
    browser = _browser(container)
    before = flow.cash_balance()

    page = _outcome(browser, _not_pay(browser, "No tiene dinero", "2026-11-02"))

    assert "No pago registrado" in page and "02/11/2026" in page
    [row] = flow._get(f"/v1/loans/{LOAN}/non-payments").json()
    assert row["reason"] == "No tiene dinero" and row["commitment_date"] == "2026-11-02"
    route = browser.get("/web/ruta").text
    assert "Pendientes (0)" in route and "No pagaron (1)" in route
    assert flow.cash_balance() == before


def test_t7b_a_double_tap_on_a_non_payment_registers_one(flow, container):
    browser = _browser(container)
    token = _field(browser.get(NON_PAYMENT_PAGE).text)

    _not_pay(browser, "No tiene dinero", "2026-11-02", token=token)
    _not_pay(browser, "No tiene dinero", "2026-11-02", token=token)

    assert len(flow._get(f"/v1/loans/{LOAN}/non-payments").json()) == 1


@pytest.mark.parametrize(
    ("reason", "day", "expected"),
    [
        ("No tiene dinero", "2026-10-30", "posterior a hoy"),
        ("No tiene dinero", "2026-10-01", "posterior a hoy"),
        ("No tiene dinero", "", "fecha de compromiso"),
        ("No tiene dinero", "mañana", "fecha de compromiso"),
        ("   ", "2026-11-02", "motivo"),
        ("", "2026-11-02", "motivo"),
    ],
)
def test_t7b_an_invalid_non_payment_is_refused_in_spanish_and_records_nothing(
    flow, container, reason, day, expected
):
    browser = _browser(container)

    page = _outcome(browser, _not_pay(browser, reason, day))

    assert expected in page
    assert flow._get(f"/v1/loans/{LOAN}/non-payments").json() == []
    assert "Pendientes (1)" in browser.get("/web/ruta").text


def test_t7b_what_the_collector_types_is_escaped_on_the_result_and_the_route(flow, container):
    browser = _browser(container)

    _not_pay(browser, "<script>alert(1)</script>", "2026-11-02")

    for html in (browser.get("/web/ruta").text,):
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_t7b_on_sunday_there_is_nothing_to_register(container, clock):
    clock.advance(timedelta(days=2))
    browser = _browser(container)

    for path in (PAYMENT_PAGE, NON_PAYMENT_PAGE):
        assert browser.get(path).status_code == 404


def test_t7b_the_symbol_of_the_currency_shows_on_the_balance_and_the_receipt():
    container = build_container(Settings(currency_symbol="$"), FakeClock(), SimulatedNotifier())
    browser = _browser(container)

    assert "Saldo $ 700,00" in browser.get(PAYMENT_PAGE).text
    assert "Pago de $ 250,00 registrado" in _outcome(browser, _pay(browser, "250,00"))


def test_t7b_without_the_device_time_the_server_time_is_used(flow, container):
    browser = _browser(container)
    token = _field(browser.get(PAYMENT_PAGE).text)

    response = browser.post(PAYMENT_PAGE, data={"ficha": token, "monto": "10,00", "medio": "EFECTIVO"})

    assert "Pago de 10,00 registrado" in _outcome(browser, response)
    assert len(_payments(flow)) == 1
