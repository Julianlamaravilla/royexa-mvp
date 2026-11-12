"""T11a: the visual identity does not break the pages' contract: one stylesheet from this origin,
no inline style or script, every icon the pages use exists in the sprite, the states of a
disbursement carry their colour, and the bottom tabs follow the box. Runs on both adapters."""

import re
from pathlib import Path

from fastapi.testclient import TestClient
from support import COLLECTOR

from royexa.api import create_app
from royexa.seed import demo_password
from royexa.web import routes

STATIC = Path(routes.HERE) / "static"


def _browser(container, user: str = COLLECTOR) -> TestClient:
    browser = TestClient(create_app(container), follow_redirects=False)
    browser.post("/web/login", data={"user_id": user, "password": demo_password(user)})
    return browser


def _pages(container, flow) -> dict[str, str]:
    flow.requested(client="cliente-3")
    browser = _browser(container)
    anonymous = TestClient(create_app(container), follow_redirects=False)
    return {
        "login": anonymous.get("/web/login").text,
        "ruta": browser.get("/web/ruta").text,
        "resultado": browser.post("/web/pago/no-hay", data={"ficha": "x"}).text,
    }


def test_t11a_the_stylesheet_has_no_external_resource_and_defines_the_palette():
    css = (STATIC / "app.css").read_text()

    assert "@import" not in css and not re.search(r"url\(\s*['\"]?https?:", css)
    for token in ("--brand:", "--accent:", "--ok:", "--bad:", "--wait:"):
        assert token in css, token
    assert (STATIC / "app.js").exists()


def test_t11a_pages_load_one_local_stylesheet_and_nothing_inline(container, flow):
    for name, html in _pages(container, flow).items():
        assert html.count('<link rel="stylesheet" href="/web/static/app.css">') == 1, name
        assert "style=" not in html and "<script>" not in html and "onclick=" not in html, name
        assert 'name="theme-color"' in html, name


def test_t11a_every_icon_a_page_uses_exists_in_the_sprite(container, flow):
    for name, html in _pages(container, flow).items():
        used = set(re.findall(r'<use href="#(i-[a-z]+)"', html))
        defined = set(re.findall(r'<symbol id="(i-[a-z]+)"', html))
        assert used <= defined, f"{name}: {used - defined}"
        assert defined, f"{name}: no sprite"


def test_t11a_the_login_has_the_brand_and_hides_nothing_behind_the_icons(container):
    html = TestClient(create_app(container)).get("/web/login").text

    assert "ROYEXA" in html and "Cobranza diaria, cuentas claras." in html
    assert re.search(r'<svg class="icon" aria-hidden="true"', html), "icons are decorative"


def test_t11a_the_route_has_tabs_and_the_one_for_the_current_page_says_so(container):
    html = _browser(container).get("/web/ruta").text

    assert '<nav class="tabs"' in html
    assert re.search(r'<a href="/web/ruta" aria-current="page">', html)
    assert 'href="/web/desembolso/nuevo"' in html and 'href="/web/cierre"' in html


def test_t11a_a_closed_box_turns_the_close_tab_into_plain_text(flow, container):
    flow.pay("prestamo-impago", 70_000)
    assert flow.close_box(70_000).status_code == 201

    html = _browser(container).get("/web/ruta").text

    assert 'class="tab-off"' in html and 'href="/web/cierre"' not in html


def test_t11a_each_state_of_a_disbursement_has_its_own_colour(flow, container):
    waiting = flow.requested(client="cliente-1")
    rejected = flow.requested(client="cliente-3")
    flow.reject(rejected["id"], reason="monto alto")
    approved = flow.approved(client="cliente-1", amount_cents=20_000)
    confirmed = flow.approved(client="cliente-3", amount_cents=20_000)
    flow.confirm(confirmed["id"], flow.issued_code(confirmed["id"]))

    html = _browser(container).get("/web/ruta").text

    for kind, label in (("wait", "En espera"), ("bad", "Rechazado"), ("info", "Aprobado"), ("ok", "Entregado")):
        assert f'<span class="badge badge-{kind}">{label}</span>' in html, (kind, waiting, approved)


def test_t11a_a_client_without_amounts_is_not_shown_with_zeros(flow, container):
    flow.pay("prestamo-impago", 30_000, "EFECTIVO")

    html = _browser(container).get("/web/ruta").text

    assert "Efectivo 300,00" in html and "Transferencia 0,00" not in html


def test_t11a_initials_use_up_to_two_words():
    assert routes.initials("María Fernanda Ruiz") == "MF"
    assert routes.initials("cobrador") == "C"
    assert routes.initials("  ") == "?"
