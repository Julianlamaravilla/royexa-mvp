"""T12 (RF-06, CA-12, EC-04): the administrator's page of notices. It lists what was sent, what
waits and what failed, with the client and the reason, retries the dispatch from a one-time
form, and the menu counts the failed ones. Runs on both adapters. FakeClock starts on Friday
2026-10-30."""

import re

import pytest
from fastapi.testclient import TestClient
from support import ADMIN, COLLECTOR

from royexa.api import create_app
from royexa.seed import demo_password
from royexa.shared.outbox import MAX_DELIVERY_ATTEMPTS

PATH = "/web/admin/avisos"
ADMIN_PAGES = [
    "/web/admin", "/web/admin/solicitudes", "/web/admin/libro", "/web/admin/clientes",
    "/web/admin/cajas", "/web/admin/descuadres", PATH,
]


def _browser(container, user: str = ADMIN) -> TestClient:
    browser = TestClient(create_app(container), follow_redirects=False)
    browser.post("/web/login", data={"user_id": user, "password": demo_password(user)})
    return browser


def _token(html: str) -> str:
    form = re.search(r'action="/web/admin/avisos/reintentar".*?</form>', html, re.S)
    assert form, "no retry form on the page"
    return re.search(r'name="ficha" value="([^"]+)"', form.group(0)).group(1)


def _retry(browser):
    response = browser.post(PATH.replace("avisos", "avisos/reintentar"), data={"ficha": _token(browser.get(PATH).text)})
    assert response.status_code == 303, response.text
    return browser.get(response.headers["location"]).text


def _section(html: str, name: str) -> str:
    found = re.search(rf'<section class="notices" id="{name}".*?</section>', html, re.S)
    return found.group(0) if found else ""


def _fail_until_failed(flow, notifier) -> None:
    notifier.failing = True
    for _ in range(MAX_DELIVERY_ATTEMPTS):
        flow.dispatch()


@pytest.fixture
def mixed(flow, notifier):
    """cliente-1: a sent code notice. cliente-3: a failed one. cliente-2: a pending payment receipt."""
    sent = flow.approved(client="cliente-1")
    flow.dispatch()
    assert flow.notices(sent["id"])[0]["status"] == "ENVIADO"
    notifier.failing = True
    failed = flow.approved(client="cliente-3")
    for _ in range(MAX_DELIVERY_ATTEMPTS):
        flow.dispatch()
    flow.pay("prestamo-impago", 20_000)
    flow.dispatch()
    return {"sent": sent, "failed": failed}


def test_t12_the_page_lists_sent_pending_and_failed_with_the_client(container, mixed):
    html = _browser(container).get(PATH).text

    for name, word, client in (
        ("fallidos", "Fallido", "Cliente"),
        ("pendientes", "Pendiente", "Cliente"),
        ("enviados", "Enviado", "Cliente"),
    ):
        section = _section(html, name)
        assert f"badge-" in section and word in section and client in section, name
        assert section.count('<li class="card">') == 1, name
    names = {c.id: c.name for c in _clients(container)}
    assert names["cliente-3"] in _section(html, "fallidos")
    assert names["cliente-2"] in _section(html, "pendientes")
    assert names["cliente-1"] in _section(html, "enviados")
    assert "Código de confirmación" in _section(html, "fallidos")
    assert "Comprobante de pago" in _section(html, "pendientes")


def _clients(container):
    return container.client_queries.all()


def test_t12_a_failed_notice_shows_its_reason_and_the_attempts(container, mixed):
    html = _browser(container).get(PATH).text
    failed = _section(html, "fallidos")

    assert 'class="badge badge-bad">Fallido<' in failed
    assert "simulated channel did not confirm the delivery" in failed
    assert f"{MAX_DELIVERY_ATTEMPTS} de {MAX_DELIVERY_ATTEMPTS} intentos" in failed
    pending = _section(html, "pendientes")
    assert 'class="badge badge-wait">Pendiente<' in pending
    assert "1 de 5 intentos" in pending and "simulated channel" in pending
    sent = _section(html, "enviados")
    assert 'class="badge badge-ok">Enviado<' in sent and "simulated channel" not in sent


def test_t12_the_counters_say_how_many_of_each(container, mixed):
    html = _browser(container).get(PATH).text

    assert re.search(r'<div class="tile t-bad"><strong>1</strong><span>fallidos</span>', html)
    assert re.search(r'<div class="tile t-wait"><strong>1</strong><span>pendientes</span>', html)
    assert re.search(r'<div class="tile t-ok"><strong>1</strong><span>enviados</span>', html)


def test_t12_an_empty_page_says_so(container):
    html = _browser(container).get(PATH).text

    assert re.search(r'<div class="empty">.*No hay avisos todavía\.', html, re.S)
    assert "avisos/reintentar" not in html, "nothing to retry"


def test_t12_a_payment_notice_names_its_client_and_kind(container, flow, notifier):
    notifier.failing = True
    flow.pay("prestamo-impago", 20_000)
    flow.dispatch()
    html = _browser(container).get(PATH).text

    assert "Comprobante de pago" in _section(html, "pendientes")


def test_t12_retrying_after_the_channel_recovers_changes_the_state(container, flow, notifier):
    notifier.failing = True
    asked = flow.approved(client="cliente-1")
    flow.dispatch()
    browser = _browser(container)
    assert "Pendiente" in browser.get(PATH).text
    notifier.failing = False

    outcome = _retry(browser)

    assert "Se envió 1 aviso" in outcome
    assert flow.notices(asked["id"])[0]["status"] == "ENVIADO"
    html = browser.get(PATH).text
    assert "Código de confirmación" in _section(html, "enviados")
    assert "Código de confirmación" not in _section(html, "pendientes")


def test_t12_retrying_while_the_channel_is_still_down_counts_one_more_attempt(container, flow, notifier):
    notifier.failing = True
    asked = flow.approved(client="cliente-1")
    flow.dispatch()
    browser = _browser(container)

    outcome = _retry(browser)

    assert "siguen sin confirmar" in outcome
    assert flow.notices(asked["id"])[0]["attempts"] == 2
    assert "2 de 5 intentos" in browser.get(PATH).text


def test_t12_the_retry_button_only_shows_while_something_is_pending(container, flow, notifier):
    _fail_until_failed(flow, notifier)
    browser = _browser(container)
    assert "avisos/reintentar" not in browser.get(PATH).text, "a failed notice leaves the queue"

    flow.approved(client="cliente-3")
    assert "avisos/reintentar" in browser.get(PATH).text
    notifier.failing = False
    flow.dispatch()
    assert "avisos/reintentar" not in browser.get(PATH).text


def test_t12_the_retry_form_is_single_use(container, flow, notifier):
    notifier.failing = True
    flow.approved(client="cliente-1")
    flow.dispatch()
    browser = _browser(container)
    token = _token(browser.get(PATH).text)
    attempts = lambda: flow.notices()[0]["attempts"]  # noqa: E731

    first = browser.post("/web/admin/avisos/reintentar", data={"ficha": token})
    again = browser.post("/web/admin/avisos/reintentar", data={"ficha": token})

    assert first.headers["location"] == again.headers["location"]
    assert attempts() == 2, "the second submit repeated nothing"


def test_t12_a_missing_or_foreign_token_does_nothing(container, flow, notifier):
    notifier.failing = True
    flow.approved(client="cliente-1")
    flow.dispatch()
    browser = _browser(container)

    for data in ({}, {"ficha": "inventada"}):
        response = browser.post("/web/admin/avisos/reintentar", data=data)
        assert response.status_code == 403
    assert flow.notices()[0]["attempts"] == 1


def test_t12_only_the_administrator_gets_in(container):
    path = PATH
    assert _browser(container, COLLECTOR).get(path).headers["location"] == "/web/ruta"
    anonymous = TestClient(create_app(container), follow_redirects=False)
    assert anonymous.get(path).headers["location"] == "/web/login"
    assert anonymous.post("/web/admin/avisos/reintentar", data={}).headers["location"] == "/web/login"


def test_t12_a_collector_cannot_retry(container, flow, notifier):
    notifier.failing = True
    flow.approved(client="cliente-1")
    flow.dispatch()
    collector = _browser(container, COLLECTOR)

    response = collector.post("/web/admin/avisos/reintentar", data={"ficha": "x"})

    assert response.headers["location"] == "/web/ruta"
    assert flow.notices()[0]["attempts"] == 1


def test_t12_the_page_reads_the_same_notices_as_the_api(container, flow, mixed):
    html = _browser(container).get(PATH).text
    api = flow.notices()

    assert len(api) == 3
    for status, name in (("ENVIADO", "enviados"), ("PENDIENTE", "pendientes"), ("FALLIDO", "fallidos")):
        expected = len([n for n in api if n["status"] == status])
        assert _section(html, name).count('<li class="card">') == expected, name


def test_t12_the_menu_counts_the_failed_notices_and_hides_the_count_at_zero(container, flow, notifier):
    browser = _browser(container)
    for path in ADMIN_PAGES:
        html = browser.get(path).text
        assert 'href="/web/admin/avisos"' in html, path
        assert 'class="count"' not in html, path

    flow.approved(client="cliente-1")
    _fail_until_failed(flow, notifier)
    for path in ADMIN_PAGES:
        html = browser.get(path).text
        assert re.search(r'<a href="/web/admin/avisos"[^>]*>.*?<span class="count">1</span>', html, re.S), path
    assert re.search(r'class="card menu" href="/web/admin/avisos">.*?<span class="count">1</span>', browser.get("/web/admin").text, re.S)


def test_t12_pending_notices_do_not_raise_the_counter(container, flow, notifier):
    notifier.failing = True
    flow.approved(client="cliente-1")
    flow.dispatch()

    assert 'class="count"' not in _browser(container).get("/web/admin").text


def test_t12_the_admin_tabs_mark_the_notices_page(container, flow):
    html = _browser(container).get(PATH).text

    assert re.findall(r'<a href="([^"]+)" aria-current="page">', html) == [PATH]
    assert '<nav class="tabs" aria-label="Administración">' in html and 'class="has-tabs"' in html
    assert re.search(r'<div class="page-head">\s*<a class="back" href="/web/admin">', html)
    assert html.count("<h1") == 1


def test_t12_nothing_inline_icons_exist_and_no_foreign_resource(container, mixed):
    html = _browser(container).get(PATH).text

    assert html.count('<link rel="stylesheet" href="/web/static/app.css">') == 1
    assert "style=" not in html and "<style" not in html and "<script>" not in html
    assert "onclick=" not in html and "onsubmit=" not in html
    assert not re.search(r"""(src|href)=["']https?://""", html)
    used = set(re.findall(r'<use href="#(i-[a-z-]+)"', html))
    assert used and used <= set(re.findall(r'<symbol id="(i-[a-z-]+)"', html))


def test_t12_the_page_never_shows_a_confirmation_code(container, flow, notifier):
    flow.approved(client="cliente-1")
    flow.dispatch()
    code = flow.notifier.delivered[0].payload["code"]
    flow.approved(client="cliente-3")
    notifier.failing = True
    flow.dispatch()

    assert code not in _browser(container).get(PATH).text
