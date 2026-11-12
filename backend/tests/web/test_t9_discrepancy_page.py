"""T9 (T9-P4): the administrator's page over the same report. Runs on both adapters."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from support import ADMIN, COLLECTOR

from royexa.api import create_app
from royexa.seed import demo_password

PAGE = "/web/admin/descuadres"
PERIOD = "?desde=2026-10-30&hasta=2026-11-02"


def _browser(container, user: str = ADMIN) -> TestClient:
    browser = TestClient(create_app(container), follow_redirects=False)
    browser.post("/web/login", data={"user_id": user, "password": demo_password(user)})
    return browser


@pytest.fixture
def timeline(flow, clock):
    flow.pay("prestamo-impago", 70_000)
    flow.close_box(65_050)
    clock.advance(timedelta(days=1))
    flow.close_box(1_000)
    clock.advance(timedelta(days=2))
    flow.close_box(0)
    return flow


def test_t9_the_admin_home_links_to_the_page(container):
    assert f'href="{PAGE}"' in _browser(container).get("/web/admin").text


def test_t9_the_page_summarizes_and_details_the_period(timeline, container):
    html = _browser(container).get(PAGE + PERIOD).text

    assert "2 descuadres" in html
    assert "Faltantes 49,50" in html and "Sobrantes 10,00" in html
    assert "30/10/2026" in html and "31/10/2026" in html and "cobrador-1" in html
    assert "-49,50" in html and "10,00" in html
    assert 'name="desde"' in html and 'name="hasta"' in html and 'value="2026-10-30"' in html
    assert "<script>" not in html and "style=" not in html and "onclick=" not in html


def test_t9_the_page_shows_the_evolution_by_day(timeline, container):
    html = _browser(container).get(PAGE + PERIOD).text

    assert "Evolución" in html
    for day in ("30/10/2026", "31/10/2026", "02/11/2026"):
        assert day in html
    assert "01/11/2026" not in html, "Sunday is not a collection day"


def test_t9_boxes_left_open_are_listed_apart(timeline, container):
    html = _browser(container).get(PAGE + PERIOD).text
    assert "Cajas sin cerrar" in html and "Ninguna" in html


def test_t9_a_box_left_open_on_a_past_day_shows_its_collector_and_day(flow, container, clock):
    flow.pay("prestamo-impago", 10_000)
    clock.advance(timedelta(days=1))

    html = _browser(container).get(PAGE + PERIOD).text

    assert "Cajas sin cerrar" in html and "cobrador-1" in html and "30/10/2026" in html
    assert "No hubo descuadres en el periodo" in html


def test_t9_without_dates_it_uses_the_current_month(timeline, container):
    html = _browser(container).get(PAGE).text

    assert 'value="2026-11-01"' in html and 'value="2026-11-02"' in html
    assert "No hubo descuadres en el periodo" in html


@pytest.mark.parametrize(
    "query", ["?desde=2026-11-02&hasta=2026-10-30", "?desde=ayer&hasta=hoy", "?desde=2020-01-01&hasta=2026-10-30"]
)
def test_t9_a_bad_period_is_explained_in_spanish(container, query):
    response = _browser(container).get(PAGE + query)

    assert response.status_code == 200
    assert "período" in response.text.lower() or "periodo" in response.text.lower()
    assert "notice error" in response.text


def test_t9_only_the_administrator_sees_it(container):
    assert _browser(container, COLLECTOR).get(PAGE).headers["location"] == "/web/ruta"
    anonymous = TestClient(create_app(container), follow_redirects=False)
    assert anonymous.get(PAGE).headers["location"] == "/web/login"
