"""T11b: at 360 px none of the new pages scrolls sideways, and the discrepancy chart fits the
screen with its bars inside the drawing. A collector closes a short box and the administrator
walks the pages the task restyled."""

import httpx
from support import PHONE, assert_fits_phone as _fits

from royexa.seed import demo_password


def _api(server, user: str) -> httpx.Client:
    client = httpx.Client(base_url=server.url)
    login = client.post("/v1/auth/login", json={"user_id": user, "password": demo_password(user)})
    client.headers["Authorization"] = f"Bearer {login.json()['token']}"
    return client


def _login(phone, server, user: str, landing: str) -> None:
    phone.goto(f"{server.url}/web/login")
    phone.fill("input[name=user_id]", user)
    phone.fill("input[name=password]", demo_password(user))
    phone.click("button[type=submit]")
    phone.wait_for_url(f"**{landing}")


def test_t11b_the_collector_forms_fit_a_phone(server, phone):
    _login(phone, server, "cobrador-1", "/web/ruta")
    loan = "prestamo-impago"
    for path in (f"/web/pago/{loan}", f"/web/no-pago/{loan}", "/web/desembolso/nuevo", "/web/cierre"):
        phone.goto(server.url + path)
        assert phone.locator(".page-head h1").count() == 1, path
        assert phone.locator("nav.tabs").is_visible(), path
        _fits(phone)


def test_t11b_the_admin_pages_and_the_chart_fit_a_phone(server, phone):
    collector = _api(server, "cobrador-1")
    pending = collector.get("/v1/routes/ruta-1/pending-visits").json()
    for row in pending:
        collector.post(
            f"/v1/loans/{row['loan_id']}/non-payments",
            json={"reason": "no estaba", "commitment_date": "2026-11-30", "device_time": "2026-10-30T14:00:00+00:00"},
        )
    closed = collector.post(
        "/v1/cash-boxes/cobrador-1/close",
        json={"delivered_cents": 1_000, "device_time": "2026-10-30T14:30:00+00:00"},
    )
    assert closed.status_code == 201

    _login(phone, server, "admin-1", "/web/admin")
    _fits(phone)
    for page in ("solicitudes", "libro", "clientes", "cajas"):
        phone.goto(f"{server.url}/web/admin/{page}")
        assert phone.locator("nav.tabs a[aria-current=page]").count() == 1, page
        _fits(phone)

    phone.goto(f"{server.url}/web/admin/descuadres?desde=2026-10-26&hasta=2026-10-31")
    _fits(phone)
    chart = phone.locator("svg.chart")
    assert chart.count() == 1
    box = chart.bounding_box()
    assert 0 <= box["x"] and box["x"] + box["width"] <= PHONE["width"], "the chart stays inside the screen"
    assert box["height"] > 80, "tall enough to read the bars"
    bars = phone.locator("svg.chart rect.bar").count()
    assert bars >= 1
    sizes = phone.locator("svg.chart rect.bar").evaluate_all(
        "rects => rects.map(r => { const b = r.getBoundingClientRect(); return [b.width, b.height]; })"
    )
    assert all(width > 2 and height > 0 for width, height in sizes), sizes
