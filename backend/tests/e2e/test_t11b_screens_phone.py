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


def test_t12_the_notices_page_and_the_six_tabs_fit_a_phone(server, phone):
    """T12: a failed notice with its reason, a pending one and the failed counter on the tab
    bar, none of it scrolling sideways at 360 px; the retry button works from the phone."""
    collector = _api(server, "cobrador-1")
    admin = _api(server, "admin-1")
    server.notifier.failing = True
    asked = collector.post(
        "/v1/disbursements",
        json={"client_id": "cliente-1", "amount_cents": 100_000, "term_days": 20, "installment_count": 20},
    ).json()
    assert admin.post(f"/v1/disbursements/{asked['id']}/approve", json={}).status_code == 200
    for _ in range(5):
        admin.post("/v1/notifications/dispatch")

    _login(phone, server, "admin-1", "/web/admin")
    _fits(phone)
    assert phone.locator("nav.tabs .count").inner_text() == "1"
    phone.goto(f"{server.url}/web/admin/avisos")
    _fits(phone)
    assert phone.locator("section#fallidos .reason").count() == 1
    assert phone.locator("nav.tabs a[aria-current=page]").count() == 1
    tabs = phone.locator("nav.tabs").bounding_box()
    assert tabs["x"] >= 0 and tabs["x"] + tabs["width"] <= PHONE["width"]
    boxes = phone.locator("nav.tabs a").evaluate_all(
        "links => links.map(a => { const b = a.getBoundingClientRect(); return [b.left, b.right]; })"
    )
    assert all(left >= 0 and right <= PHONE["width"] for left, right in boxes), boxes

    server.notifier.failing = False
    other = collector.post(
        "/v1/disbursements",
        json={"client_id": "cliente-3", "amount_cents": 50_000, "term_days": 20, "installment_count": 20},
    ).json()
    admin.post(f"/v1/disbursements/{other['id']}/approve", json={})
    phone.goto(f"{server.url}/web/admin/avisos")
    phone.click("button:has-text('Reintentar envío')")
    phone.wait_for_url("**/web/resultado/**")
    assert "Se envió 1 aviso" in phone.inner_text("body")
    _fits(phone)
    phone.goto(f"{server.url}/web/admin/avisos")
    assert phone.locator("section#enviados").count() == 1
    _fits(phone)


def test_t13_the_client_and_loan_pages_fit_a_phone(server, phone):
    """T13: the schedule of 20 installments is a stack of cards, the progress bar is drawn and
    nothing scrolls sideways at 360 px, for the administrator and for the collector."""
    collector = _api(server, "cobrador-1")
    admin = _api(server, "admin-1")
    asked = collector.post(
        "/v1/disbursements",
        json={"client_id": "cliente-1", "amount_cents": 100_000, "term_days": 20, "installment_count": 20},
    ).json()
    admin.post(f"/v1/disbursements/{asked['id']}/approve", json={})
    server.notifier.failing = False
    admin.post("/v1/notifications/dispatch")
    code = next(s.payload["code"] for s in server.notifier.delivered if "code" in s.payload)
    done = collector.post(
        f"/v1/disbursements/{asked['id']}/confirm",
        json={"code": code, "device_time": "2026-10-30T13:59:00+00:00"},
    )
    assert done.status_code == 200, done.text
    loan = done.json()["loan"]["id"]
    collector.post(
        f"/v1/loans/{loan}/payments",
        json={"amount_cents": 3_000, "method": "EFECTIVO", "device_time": "2026-10-30T14:00:00+00:00"},
    )

    for user, landing in (("admin-1", "/web/admin"), ("cobrador-1", "/web/ruta")):
        phone.context.clear_cookies()
        _login(phone, server, user, landing)
        phone.goto(f"{server.url}/web/clientes/cliente-1")
        assert phone.locator(f"a[href='/web/prestamos/{loan}']").count() == 1
        _fits(phone)
        phone.goto(f"{server.url}/web/prestamos/{loan}")
        _fits(phone)
        assert phone.locator("li.inst").count() == 20
        bar = phone.locator("[role=progressbar]").bounding_box()
        assert 0 <= bar["x"] and bar["x"] + bar["width"] <= PHONE["width"] and bar["height"] >= 8
        rows = phone.locator("li.inst").evaluate_all(
            "items => items.map(i => { const b = i.getBoundingClientRect(); return [b.left, b.right]; })"
        )
        assert all(left >= 0 and right <= PHONE["width"] for left, right in rows), rows
        assert "19,5 de 20" in phone.inner_text("body")


def test_t14a_the_adjustment_and_the_exception_work_from_a_phone(server, phone):
    """T14a (CA-08, CA-10): the administrator adjusts a payment and authorizes a renewal by
    tapping, and the ledger shows the original with its adjustment inside 360 px."""
    collector = _api(server, "cobrador-1")
    paid = collector.post(
        "/v1/loans/prestamo-impago/payments",
        json={"amount_cents": 3_000, "method": "EFECTIVO", "device_time": "2026-10-30T14:00:00+00:00"},
    )
    assert paid.status_code == 201, paid.text

    _login(phone, server, "admin-1", "/web/admin")
    phone.goto(f"{server.url}/web/admin/libro")
    _fits(phone)
    phone.click("a:has-text('Ajustar')")
    _fits(phone)
    phone.fill("input[name=importe]", "-5,00")
    phone.fill("input[name=motivo]", "se cobró de menos")
    phone.click("button:has-text('Registrar ajuste')")
    phone.wait_for_url("**/web/resultado/**")
    assert "Ajuste registrado" in phone.inner_text("body")
    _fits(phone)
    phone.goto(f"{server.url}/web/admin/libro")
    _fits(phone)
    group = phone.locator("li.card", has=phone.locator("ul.adjustments"))
    assert group.count() == 1
    assert "se cobró de menos" in group.inner_text() and "-5,00" in group.inner_text()
    box = group.bounding_box()
    assert 0 <= box["x"] and box["x"] + box["width"] <= PHONE["width"]

    phone.goto(f"{server.url}/web/clientes/cliente-2")
    _fits(phone)
    phone.fill("input[name=motivo]", "cliente recurrente")
    phone.click("button:has-text('Autorizar renovación')")
    phone.wait_for_url("**/web/resultado/**")
    assert "Excepción registrada" in phone.inner_text("body")
    _fits(phone)

    asked = collector.post(
        "/v1/disbursements",
        json={"client_id": "cliente-2", "amount_cents": 100_000, "term_days": 20, "installment_count": 20},
    )
    assert asked.status_code == 201, "CA-10: with the exception the renewal is allowed"
