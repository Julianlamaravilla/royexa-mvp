"""T14a (RF-04, CA-08, CA-10): the administrator corrects a ledger entry with a signed
adjustment and authorizes a renewal exception from the browser, through the same use cases
as the API. The ledger shows the original next to its compensating entry and the original
never changes. Runs on both adapters. FakeClock starts on Friday 2026-10-30."""

import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from support import ADMIN, COLLECTOR

from royexa.api import create_app
from royexa.seed import demo_password

LEDGER = "/web/admin/libro"


def _browser(container, user: str = ADMIN) -> TestClient:
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


def _page(entry_id: str) -> str:
    return f"/web/admin/libro/{entry_id}/ajuste"


def _adjust(browser, entry_id, amount="-25,00", reason="error de captura", token=None):
    token = token or _field(browser.get(_page(entry_id)).text)
    return browser.post(_page(entry_id), data={"ficha": token, "importe": amount, "motivo": reason})


@pytest.fixture
def paid(flow, clock):
    """A loan from yesterday and a cash payment of 300,00 today; returns its ledger entry."""
    clock.advance(-timedelta(days=1))
    loan = flow.confirmed(client="cliente-1")["loan"]
    clock.advance(timedelta(days=1))
    payment = flow.pay(loan["id"], 30_000).json()["payment"]
    return flow.payment_entry(payment["id"])


# ---- the adjustment form ----------------------------------------------------------------


def test_t14a_the_ledger_offers_an_adjust_link_for_each_original_entry(container, paid):
    html = _browser(container).get(LEDGER).text

    assert f'href="{_page(paid["id"])}"' in html and "Ajustar" in html


def test_t14a_the_form_shows_the_original_and_asks_for_a_signed_amount_and_a_motive(container, paid):
    html = _browser(container).get(_page(paid["id"])).text

    assert "PAGO" in html and "300,00" in html
    assert re.search(r'<input[^>]*name="importe"[^>]*required', html)
    assert re.search(r'name="motivo"[^>]*required|required[^>]*name="motivo"', html)
    assert _field(html)
    assert "<script>" not in html and "style=" not in html and "onclick=" not in html


def test_t14a_a_negative_adjustment_is_registered_as_a_new_entry_next_to_the_original(
    flow, container, paid
):
    browser = _browser(container)
    before = {e["id"]: e for e in flow.ledger()}

    text = _outcome(browser, _adjust(browser, paid["id"], "-25,00", "error de captura"))

    assert "Ajuste registrado" in text
    after = {e["id"]: e for e in flow.ledger()}
    assert after[paid["id"]] == before[paid["id"]] == paid, "the original is exactly as it was"
    [new] = [e for e in after.values() if e["id"] not in before]
    assert (new["entry_type"], new["amount_cents"], new["adjusts_entry_id"]) == ("AJUSTE", -2_500, paid["id"])
    assert new["reason"] == "error de captura" and new["actor_id"] == ADMIN


def test_t14a_a_positive_signed_amount_is_accepted(flow, container, paid):
    browser = _browser(container)

    for amount in ("+10,50", "1.000"):
        assert "Ajuste registrado" in _outcome(browser, _adjust(browser, paid["id"], amount))

    adjusted = [e["amount_cents"] for e in flow.ledger() if e["entry_type"] == "AJUSTE"]
    assert sorted(adjusted) == [1_050, 100_000]


def test_t14a_the_ledger_shows_the_original_and_its_adjustment_together(container, paid, flow):
    browser = _browser(container)
    _outcome(browser, _adjust(browser, paid["id"], "-25,00", "error de captura"))

    html = browser.get(LEDGER).text

    start, end = html.index('badge-ok">PAGO'), html.index("AJUSTE")
    group = html[start : html.index("</li>", end)]
    assert start < end and '<li class="card">' not in html[start:end], "one card holds both"
    assert '<ul class="adjustments">' in html[start:end] and "Ajustes" in html[start:end]
    assert "-25,00" in group and "error de captura" in group and "300,00" in html[start - 400 : end]
    assert html.count("AJUSTE") == 1


def test_t14a_the_original_never_changes_after_several_adjustments(flow, container, paid):
    browser = _browser(container)
    for amount in ("-5,00", "+2,00", "-1,00"):
        _outcome(browser, _adjust(browser, paid["id"], amount))

    entries = {e["id"]: e for e in flow.ledger()}
    assert entries[paid["id"]] == paid
    assert [e["entry_type"] for e in entries.values()].count("AJUSTE") == 3
    assert "300,00" in browser.get(LEDGER).text


# ---- validation -------------------------------------------------------------------------


@pytest.mark.parametrize("amount", ["0", "0,00", "-0,00", "", "abc", "25.50", "--5", "1,234"])
def test_t14a_a_zero_or_unclear_amount_is_refused_in_spanish(flow, container, paid, amount):
    browser = _browser(container)
    before = len(flow.ledger())

    text = _outcome(browser, _adjust(browser, paid["id"], amount))

    assert "importe" in text.lower() and "No se pudo completar" in text
    assert len(flow.ledger()) == before


def test_t14a_the_motive_is_required(flow, container, paid):
    browser = _browser(container)
    before = len(flow.ledger())

    for reason in ("", "   "):
        text = _outcome(browser, _adjust(browser, paid["id"], "-5,00", reason))
        assert "motivo" in text.lower() and "No se pudo completar" in text

    assert len(flow.ledger()) == before


def test_t14a_a_missing_entry_is_a_404_page(container):
    response = _browser(container).get(_page("no-existe"))

    assert response.status_code == 404 and "asiento" in response.text.lower()


def test_t14a_the_form_token_works_once_and_a_repeat_adjusts_nothing_more(flow, container, paid):
    browser = _browser(container)
    token = _field(browser.get(_page(paid["id"])).text)
    before = len(flow.ledger())

    first = _adjust(browser, paid["id"], "-5,00", token=token)
    again = _adjust(browser, paid["id"], "-5,00", token=token)

    assert first.headers["location"] == again.headers["location"]
    assert len(flow.ledger()) == before + 1


def test_t14a_a_form_without_a_valid_token_does_nothing(flow, container, paid):
    browser = _browser(container)
    before = len(flow.ledger())

    response = browser.post(_page(paid["id"]), data={"importe": "-5,00", "motivo": "x"})

    assert response.status_code == 403 and len(flow.ledger()) == before


# ---- a closed box: the adjustment waits for the next day (T5-P4) ------------------------


def test_t14a_with_the_box_closed_the_adjustment_is_refused_and_the_next_day_it_lands_in_the_new_box(
    flow, container, clock, paid
):
    browser = _browser(container)
    flow.visit_everyone()
    closed = flow.close_box(30_000).json()
    friday = flow._get(f"/v1/cash-boxes/{COLLECTOR}", ADMIN).json()["balance_cents"]

    refused = _outcome(browser, _adjust(browser, paid["id"], "-25,00"))

    assert "No se pudo completar" in refused and "mañana" in refused and "cierre no cambia" in refused
    assert [e["entry_type"] for e in flow.ledger()].count("AJUSTE") == 0

    clock.advance(timedelta(days=1))
    browser = _browser(container)  # the session of yesterday lapsed with the clock
    assert "Ajuste registrado" in _outcome(browser, _adjust(browser, paid["id"], "-25,00"))

    [adjustment] = [e for e in flow.ledger() if e["entry_type"] == "AJUSTE"]
    assert adjustment["cash_box_id"] == "caja-cobrador-1-2026-10-31"
    friday_box = flow._get(f"/v1/cash-boxes/{COLLECTOR}?date=2026-10-30", ADMIN).json()
    assert friday_box["balance_cents"] == friday, "the closed box is untouched"
    assert flow.cash_closes().json() == [closed], "and so is its close"
    assert {e["id"]: e for e in flow.ledger()}[paid["id"]] == paid


# ---- who can ----------------------------------------------------------------------------


def test_t14a_a_collector_cannot_open_or_send_the_form(flow, container, paid):
    collector = _browser(container, COLLECTOR)
    admin = _browser(container)
    token = _field(admin.get(_page(paid["id"])).text)
    before = len(flow.ledger())

    assert collector.get(_page(paid["id"])).headers["location"] == "/web/ruta"
    assert collector.post(_page(paid["id"]), data={"ficha": token, "importe": "-1", "motivo": "x"}).status_code in (303, 403)
    assert len(flow.ledger()) == before


def test_t14a_without_a_session_the_form_leads_to_the_login(container, paid):
    anonymous = TestClient(create_app(container), follow_redirects=False)

    assert anonymous.get(_page(paid["id"])).headers["location"] == "/web/login"
    assert anonymous.post(_page(paid["id"]), data={}).headers["location"] == "/web/login"


def test_t14a_the_adjustment_text_is_escaped(flow, container, paid):
    browser = _browser(container)
    _outcome(browser, _adjust(browser, paid["id"], "-1,00", "<b>mal</b>"))

    html = browser.get(LEDGER).text

    assert "<b>mal</b>" not in html and "&lt;b&gt;mal&lt;/b&gt;" in html


# ---- the renewal exception (RN-05, CA-10) -----------------------------------------------

CLIENT_WITH_BALANCE = "cliente-2"
CLIENT_PAGE = f"/web/clientes/{CLIENT_WITH_BALANCE}"
EXCEPTION = f"/web/admin/clientes/{CLIENT_WITH_BALANCE}/excepcion"


def _grant(browser, reason="cliente recurrente", token=None):
    token = token or _field(re.search(r'action="[^"]*excepcion".*?</form>', browser.get(CLIENT_PAGE).text, re.S).group(0))
    return browser.post(EXCEPTION, data={"ficha": token, "motivo": reason})


def _ask(browser, client):
    token = _field(browser.get("/web/desembolso/nuevo").text)
    return _outcome(
        browser,
        browser.post(
            "/web/desembolso/nuevo",
            data={"ficha": token, "cliente": client, "monto": "100,00", "plazo": "20", "cuotas": "20"},
        ),
    )


def test_t14a_the_client_page_offers_the_exception_only_with_an_unsettled_loan(container):
    admin = _browser(container)

    with_balance = admin.get(CLIENT_PAGE).text
    settled = admin.get("/web/clientes/cliente-3").text
    none = admin.get("/web/clientes/cliente-1").text

    assert f'action="{EXCEPTION}"' in with_balance and "Autorizar renovación" in with_balance
    assert "excepcion" not in settled and "excepcion" not in none
    assert 'name="motivo"' in with_balance


def test_t14a_a_collector_does_not_see_the_exception_form(container):
    assert "excepcion" not in _browser(container, COLLECTOR).get(CLIENT_PAGE).text


def test_ca10_the_exception_lets_the_collector_renew_a_client_with_a_balance(flow, container):
    admin, collector = _browser(container), _browser(container, COLLECTOR)

    blocked = _ask(collector, CLIENT_WITH_BALANCE)
    assert "No se pudo completar" in blocked and "sin liquidar" in blocked

    granted = _outcome(admin, _grant(admin, "cliente recurrente"))
    assert "Excepción registrada" in granted

    allowed = _ask(collector, CLIENT_WITH_BALANCE)
    assert "No se pudo completar" not in allowed and "sin liquidar" not in allowed
    assert re.search(r"/web/desembolso/(?!nuevo)", collector.get("/web/ruta").text)


def test_ca10_the_exception_is_single_use_and_registered_with_its_reason(flow, container):
    admin = _browser(container)

    _outcome(admin, _grant(admin, "cliente recurrente"))

    with container.context.uow() as uow:
        exception = uow.loans.open_exception_for(CLIENT_WITH_BALANCE)
    assert exception.reason == "cliente recurrente" and exception.granted_by == ADMIN
    assert exception.consumed_by is None


def test_ca10_the_reason_is_required(container):
    admin = _browser(container)

    for reason in ("", "  "):
        text = _outcome(admin, _grant(admin, reason))
        assert "No se pudo completar" in text and "motivo" in text.lower()
    with container.context.uow() as uow:
        assert uow.loans.open_exception_for(CLIENT_WITH_BALANCE) is None


def test_ca10_a_form_of_one_client_cannot_grant_an_exception_to_another(container):
    admin = _browser(container)
    token = _field(admin.get(CLIENT_PAGE).text)

    response = admin.post(
        "/web/admin/clientes/cliente-1/excepcion", data={"ficha": token, "motivo": "x"}
    )

    assert response.status_code == 403
    with container.context.uow() as uow:
        assert uow.loans.open_exception_for("cliente-1") is None


def test_ca10_only_an_administrator_grants_it_and_without_a_session_nobody(container):
    admin = _browser(container)
    token = _field(re.search(r'action="[^"]*excepcion".*?</form>', admin.get(CLIENT_PAGE).text, re.S).group(0))

    collector = _browser(container, COLLECTOR)
    assert collector.post(EXCEPTION, data={"ficha": token, "motivo": "x"}).headers["location"] == "/web/ruta"
    anonymous = TestClient(create_app(container), follow_redirects=False)
    assert anonymous.post(EXCEPTION, data={}).headers["location"] == "/web/login"
    with container.context.uow() as uow:
        assert uow.loans.open_exception_for(CLIENT_WITH_BALANCE) is None


def test_ca10_a_repeated_form_registers_one_exception(container):
    admin = _browser(container)
    token = _field(re.search(r'action="[^"]*excepcion".*?</form>', admin.get(CLIENT_PAGE).text, re.S).group(0))

    first = _grant(admin, token=token)
    again = _grant(admin, token=token)

    assert first.headers["location"] == again.headers["location"]
