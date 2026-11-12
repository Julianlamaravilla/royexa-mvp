"""T7d: the collector closes the day's box from the web and sees the discrepancy.

Runs on both adapters. FakeClock starts on Friday 2026-10-30. The route of cobrador-1 holds
one client with a loan, so the box can close once that client paid or was visited.
"""

import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from support import ADMIN, COLLECTOR

from royexa.api import create_app
from royexa.seed import demo_password

CLOSE_PAGE = "/web/cierre"


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


def _close(browser, delivered: str, token=None):
    token = token or _field(browser.get(CLOSE_PAGE).text)
    return browser.post(
        CLOSE_PAGE,
        data={"ficha": token, "entregado": delivered, "device_time": "2026-10-30T18:00:00Z"},
    )


def _closes(flow) -> list[dict]:
    return flow.cash_closes().json()


def test_t7d_the_route_offers_the_close_only_while_the_box_is_open(flow, container):
    browser = _browser(container)
    assert f'href="{CLOSE_PAGE}"' in browser.get("/web/ruta").text

    flow.pay("prestamo-impago", 70_000)
    assert flow.close_box(70_000).status_code == 201

    assert f'href="{CLOSE_PAGE}"' not in browser.get("/web/ruta").text


def test_t7d_with_clients_pending_the_page_says_so_and_offers_no_form(container):
    html = _browser(container).get(CLOSE_PAGE).text

    assert "pendientes de visita" in html and "Cliente con saldo pendiente" in html
    assert 'name="entregado"' not in html


def test_t7d_without_pending_clients_the_page_asks_for_the_cash_delivered(flow, container):
    flow.pay("prestamo-impago", 70_000)

    html = _browser(container).get(CLOSE_PAGE).text

    assert 'name="entregado"' in html and 'name="ficha"' in html and 'name="device_time"' in html
    assert "irreversible" in html.lower()
    assert "<script>" not in html and "style=" not in html and "onclick=" not in html


def test_t7d_an_exact_delivery_closes_the_box_without_a_discrepancy(flow, container):
    flow.pay("prestamo-impago", 70_000)
    browser = _browser(container)

    page = _outcome(browser, _close(browser, "700,00"))

    assert "Caja cerrada" in page and "Sin descuadre" in page
    assert "Esperado 700,00" in page and "Entregado 700,00" in page
    [close] = _closes(flow)
    assert close["expected_cents"] == close["delivered_cents"] == 70_000
    assert close["discrepancy_cents"] == 0


def test_t7d_a_short_delivery_shows_how_much_is_missing(flow, container):
    flow.pay("prestamo-impago", 70_000)
    browser = _browser(container)

    page = _outcome(browser, _close(browser, "650,50"))

    assert "Caja cerrada" in page and "Faltan 49,50" in page
    assert _closes(flow)[0]["discrepancy_cents"] == -4_950


def test_t7d_a_surplus_shows_how_much_is_left_over(flow, container):
    flow.pay("prestamo-impago", 70_000)
    browser = _browser(container)

    page = _outcome(browser, _close(browser, "1.000,00"))

    assert "Sobran 300,00" in page
    assert _closes(flow)[0]["discrepancy_cents"] == 30_000


def test_t7d_transfers_do_not_count_as_expected_cash(flow, container):
    flow.pay("prestamo-impago", 20_000, "EFECTIVO")
    flow.pay("prestamo-impago", 30_000, "TRANSFERENCIA")
    browser = _browser(container)

    page = _outcome(browser, _close(browser, "200,00"))

    assert "Esperado 200,00" in page and "Sin descuadre" in page


def test_t7d_zero_delivered_is_a_valid_amount(flow, container):
    flow.pay("prestamo-impago", 70_000, "TRANSFERENCIA")
    browser = _browser(container)

    page = _outcome(browser, _close(browser, "0"))

    assert "Caja cerrada" in page and "Sin descuadre" in page


def test_t7d_after_the_close_the_route_shows_the_box_closed_with_its_discrepancy(flow, container):
    flow.pay("prestamo-impago", 70_000)
    browser = _browser(container)
    _close(browser, "650,50")

    html = browser.get("/web/ruta").text

    assert "Caja cerrada" in html and "Faltan 49,50" in html
    assert f'href="{CLOSE_PAGE}"' not in html
    assert "ya está cerrada" in browser.get(CLOSE_PAGE).text


def test_t7d_a_double_tap_or_a_resend_closes_once(flow, container):
    flow.pay("prestamo-impago", 70_000)
    browser = _browser(container)
    token = _field(browser.get(CLOSE_PAGE).text)

    first = _close(browser, "700,00", token=token)
    second = _close(browser, "700,00", token=token)

    assert first.headers["location"] == second.headers["location"]
    assert "Caja cerrada" in _outcome(browser, second)
    assert len(_closes(flow)) == 1


def test_t7d_a_client_still_pending_blocks_the_close_in_spanish(flow, container):
    browser = _browser(container)
    flow.pay("prestamo-impago", 70_000)
    token = _field(browser.get(CLOSE_PAGE).text)
    new_client = flow._post("/v1/clients", ADMIN, {"name": "Otro", "route_id": "ruta-1"}).json()
    flow.confirmed(client=new_client["id"])

    page = _outcome(browser, _close(browser, "700,00", token=token))

    assert "pendientes de visita" in page and "No se pudo completar" in page
    assert _closes(flow) == []
    assert f'href="{CLOSE_PAGE}"' in browser.get("/web/ruta").text, "the box is still open"


def test_t7d_a_stale_form_on_a_closed_box_is_refused_in_spanish(flow, container):
    flow.pay("prestamo-impago", 70_000)
    browser = _browser(container)
    stale = _field(browser.get(CLOSE_PAGE).text)
    assert flow.close_box(70_000).status_code == 201

    page = _outcome(browser, _close(browser, "700,00", token=stale))

    assert "caja del día ya está cerrada" in page
    assert len(_closes(flow)) == 1


@pytest.mark.parametrize("amount", ["", "abc", "-5", "10.50", "1,234", "1.2.3"])
def test_t7d_an_amount_that_is_not_clear_is_refused_and_the_box_stays_open(flow, container, amount):
    flow.pay("prestamo-impago", 70_000)
    browser = _browser(container)

    page = _outcome(browser, _close(browser, amount))

    assert "importe" in page.lower() and f'href="{CLOSE_PAGE}"' in page
    assert _closes(flow) == []


def test_t7d_a_forged_or_foreign_token_closes_nothing(flow, container):
    flow.pay("prestamo-impago", 70_000)
    mine, other = _browser(container), _browser(container, "cobrador-2")
    token = _field(mine.get(CLOSE_PAGE).text)

    assert mine.post(CLOSE_PAGE, data={"entregado": "700,00"}).status_code == 403
    assert mine.post(CLOSE_PAGE, data={"ficha": "inventada", "entregado": "700,00"}).status_code == 403
    assert _close(other, "700,00", token=token).status_code == 403
    assert _closes(flow) == []


def test_t7d_the_administrator_and_visitors_do_not_close_boxes(container):
    assert _browser(container, ADMIN).get(CLOSE_PAGE).headers["location"] == "/web/admin"
    anonymous = TestClient(create_app(container), follow_redirects=False)
    assert anonymous.get(CLOSE_PAGE).headers["location"] == "/web/login"
    assert anonymous.post(CLOSE_PAGE, data={"ficha": "x"}).headers["location"] == "/web/login"


def test_t7d_on_sunday_there_is_no_box_to_close(container, clock):
    clock.advance(timedelta(days=2))

    html = _browser(container).get(CLOSE_PAGE).text

    assert "no es día de cobranza" in html and 'name="entregado"' not in html
