"""T13 (RF-05, CA-09, RN-01): the page of a client with his loans and the page of a loan with its
schedule, the fractional counter in a progress bar, and its payments and non-payments. Runs on
both adapters. FakeClock starts on Friday 2026-10-30."""

import re
from datetime import date
from fractions import Fraction

import pytest
from fastapi.testclient import TestClient
from support import ADMIN, COLLECTOR

from royexa.api import create_app
from royexa.seed import demo_password
from royexa.web.format import installments_text

OTHER_COLLECTOR = "cobrador-2"


def _browser(container, user: str = ADMIN) -> TestClient:
    browser = TestClient(create_app(container), follow_redirects=False)
    browser.post("/web/login", data={"user_id": user, "password": demo_password(user)})
    return browser


@pytest.fixture
def loan(flow) -> str:
    """cliente-1 gets 1.000,00 in 20 installments with a fixed interest of 200: 20 of 60."""
    return flow.confirmed(client="cliente-1")["loan"]["id"]


def _page(container, loan_id: str, user: str = ADMIN) -> str:
    response = _browser(container, user).get(f"/web/prestamos/{loan_id}")
    assert response.status_code == 200, response.text
    return response.text


def _installments(html: str) -> list[str]:
    return re.findall(r'<li class="inst[ "].*?</li>', html, re.S)


def test_t13_the_client_page_lists_his_loans_with_links_and_the_counter(container, flow, loan):
    html = _browser(container).get("/web/clientes/cliente-1").text

    assert "Cliente sin prestamos" in html and "ruta-1" in html
    assert f'href="/web/prestamos/{loan}"' in html
    assert "20 de 20" in html and "Activo" in html
    assert html.count('class="page-head"') == 1 and html.count("<h1") == 1


def test_t13_a_settled_loan_says_so_and_a_client_without_loans_has_an_empty_state(container):
    browser = _browser(container)

    settled = browser.get("/web/clientes/cliente-3").text
    assert "Liquidado" in settled and "0 de 1" in settled
    assert re.search(r'<div class="empty">.*Todavía no tiene préstamos\.', browser.get("/web/clientes/cliente-1").text, re.S)


def test_t13_ca09_the_schedule_shows_20_installments_of_60_and_never_a_sunday(container, loan):
    html = _page(container, loan)
    rows = _installments(html)

    assert len(rows) == 20
    assert all("60,00" in row for row in rows)
    days = [date.fromisoformat(d) for d in re.findall(r'<time datetime="([\d-]+)"', html)]
    assert len(days) == 20 and days == sorted(days) and days[0] == date(2026, 10, 31)
    assert all(day.isoweekday() != 7 for day in days), "a collection day is Monday to Saturday"
    assert [int(n) for n in re.findall(r'class="inst-n">(\d+)<', html)] == list(range(1, 21))


def test_t13_the_counter_is_fractional_after_a_partial_payment(container, flow, loan):
    assert flow.pay(loan, 3_000).status_code == 201

    html = _page(container, loan)

    assert "19,5 de 20" in html
    rows = _installments(html)
    assert "Parcial" in rows[0] and "30,00" in rows[0]
    assert all("Pendiente" in row for row in rows[1:])
    assert html.count("Pagada") == 0


def test_t13_a_full_installment_is_marked_paid_and_the_oldest_one_goes_first(container, flow, loan):
    flow.pay(loan, 9_000)  # one and a half installments

    rows = _installments(_page(container, loan))

    assert "Pagada" in rows[0] and "Parcial" in rows[1] and "30,00" in rows[1]
    assert all("Pendiente" in row for row in rows[2:])


def _bar(html: str) -> str:
    found = re.search(r'<div class="progress"[^>]*role="progressbar".*?</div>', html, re.S)
    assert found, "no progress bar"
    return found.group(0)


def test_t13_the_progress_bar_is_an_accessible_server_drawn_svg_proportional_to_the_paid_share(container, flow, loan):
    flow.pay(loan, 3_000)  # half of one installment of 20: 0,5 paid

    bar = _bar(_page(container, loan))

    assert 'aria-valuemin="0"' in bar and 'aria-valuemax="20"' in bar and 'aria-valuenow="0.5"' in bar
    assert 'aria-valuetext="Faltan 19,5 de 20 cuotas"' in bar
    assert "<svg" in bar and "style=" not in bar
    width = float(re.search(r'<rect class="fill" [^>]*width="([\d.]+)"', bar).group(1))
    assert width == pytest.approx(2.5)  # 0,5 of 20 installments of a bar 100 wide
    assert float(re.search(r'<rect class="track" [^>]*width="([\d.]+)"', bar).group(1)) == 100


def test_t13_the_bar_is_empty_at_the_start_and_full_when_settled(container, flow, loan):
    assert 'aria-valuenow="0"' in _bar(_page(container, loan))
    assert float(re.search(r'<rect class="fill" [^>]*width="([\d.]+)"', _bar(_page(container, loan))).group(1)) == 0
    settled = _bar(_page(container, "prestamo-liquidado"))
    assert 'aria-valuenow="1"' in settled and 'aria-valuemax="1"' in settled
    assert float(re.search(r'<rect class="fill" [^>]*width="([\d.]+)"', settled).group(1)) == 100


def test_t13_the_counter_is_written_in_spanish_without_rounding():
    assert installments_text(Fraction(39, 2)) == "19,5"
    assert installments_text(Fraction(20)) == "20"
    assert installments_text(Fraction(1, 4)) == "0,25"
    assert installments_text(Fraction(113, 6)) == "18 y 5/6"  # no finite decimal: whole and fraction
    assert installments_text(Fraction(5, 6)) == "5/6"


def test_t13_payments_and_non_payments_are_listed_with_their_data(container, flow, loan):
    flow.pay(loan, 3_000, method="EFECTIVO")
    flow.pay(loan, 1_000, method="TRANSFERENCIA")
    flow.non_pay(loan, reason="no estaba en casa", commitment_date="2026-11-02")

    html = _page(container, loan)

    payments = re.search(r'<section id="pagos".*?</section>', html, re.S).group(0)
    assert payments.count('<li class="card">') == 2
    assert "30,00" in payments and "Efectivo" in payments
    assert "10,00" in payments and "Transferencia" in payments
    refusals = re.search(r'<section id="no-pagos".*?</section>', html, re.S).group(0)
    assert refusals.count('<li class="card">') == 1
    assert "no estaba en casa" in refusals and "02/11/2026" in refusals


def test_t13_without_payments_or_refusals_the_lists_say_so(container, loan):
    html = _page(container, loan)

    assert "Todavía no hay pagos." in html and "Todavía no hay no pagos." in html


def test_t13_the_loan_page_links_back_to_its_client(container, loan):
    assert 'class="back" href="/web/clientes/cliente-1"' in _page(container, loan)


def test_t13_the_admin_clients_list_links_to_each_client(container):
    html = _browser(container).get("/web/admin/clientes").text

    for client in ("cliente-1", "cliente-2", "cliente-3", "cliente-4"):
        assert f'href="/web/clientes/{client}"' in html


def test_t13_the_day_route_links_each_client_and_the_collector_follows_it(container):
    browser = _browser(container, COLLECTOR)
    html = browser.get("/web/ruta").text

    assert 'href="/web/clientes/cliente-2"' in html
    assert browser.get("/web/clientes/cliente-2").status_code == 200


def test_t13_the_collector_sees_the_clients_and_loans_of_his_route_with_his_menu(container, loan):
    browser = _browser(container, COLLECTOR)

    client = browser.get("/web/clientes/cliente-1")
    assert client.status_code == 200 and 'aria-label="Navegación"' in client.text
    assert 'class="back" href="/web/ruta"' in client.text
    assert browser.get(f"/web/prestamos/{loan}").status_code == 200
    admin = _browser(container).get("/web/clientes/cliente-1").text
    assert 'aria-label="Administración"' in admin and 'class="back" href="/web/admin/clientes"' in admin


def test_t13_a_collector_of_another_route_is_refused_with_a_message(container, loan):
    other = _browser(container, OTHER_COLLECTOR)

    for path in ("/web/clientes/cliente-1", f"/web/prestamos/{loan}", "/web/prestamos/prestamo-impago"):
        response = other.get(path)
        assert response.status_code == 404, path
        assert "Sin acceso" in response.text or "No se encontró" in response.text
        assert "Cliente sin prestamos" not in response.text and "60,00" not in response.text
    assert other.get("/web/clientes/cliente-4").status_code == 200


def test_t13_the_administrator_sees_every_route(container):
    browser = _browser(container)

    assert browser.get("/web/clientes/cliente-4").status_code == 200
    assert browser.get("/web/prestamos/prestamo-impago").status_code == 200


def test_t13_unknown_ids_are_not_found_and_no_session_goes_to_the_login(container):
    browser = _browser(container)
    anonymous = TestClient(create_app(container), follow_redirects=False)

    assert browser.get("/web/clientes/no-existe").status_code == 404
    assert browser.get("/web/prestamos/no-existe").status_code == 404
    for path in ("/web/clientes/cliente-1", "/web/prestamos/prestamo-impago"):
        response = anonymous.get(path)
        assert response.status_code == 303 and response.headers["location"] == "/web/login"


def test_t13_the_pages_have_nothing_inline_and_every_icon_exists(container, flow, loan):
    flow.pay(loan, 3_000)
    pages = [
        _browser(container).get("/web/clientes/cliente-1").text,
        _page(container, loan),
        _page(container, loan, COLLECTOR),
    ]
    for html in pages:
        assert "style=" not in html and "<style" not in html
        assert "<script>" not in html and "onclick=" not in html
        assert not re.search(r"""(src|href)=["']https?://""", html)
        used = set(re.findall(r'<use href="#(i-[a-z-]+)"', html))
        assert used and used <= set(re.findall(r'<symbol id="(i-[a-z-]+)"', html))
