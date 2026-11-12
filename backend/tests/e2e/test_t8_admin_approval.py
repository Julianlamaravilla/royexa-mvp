"""T8: a real browser at 360 px lets the administrator approve a disbursement that a collector
requested, and the client's code goes out. The collector's request comes through the API."""

import httpx
from support import assert_fits_phone as _fits

from royexa.seed import demo_password


def _api(server, user: str) -> httpx.Client:
    client = httpx.Client(base_url=server.url)
    login = client.post("/v1/auth/login", json={"user_id": user, "password": demo_password(user)})
    client.headers["Authorization"] = f"Bearer {login.json()['token']}"
    return client


def test_t8_the_administrator_approves_a_disbursement_from_the_phone(server, phone):
    collector = _api(server, "cobrador-1")
    asked = collector.post(
        "/v1/disbursements",
        json={"client_id": "cliente-1", "amount_cents": 100_000, "term_days": 20, "installment_count": 20},
    )
    assert asked.status_code == 201
    disbursement_id = asked.json()["id"]

    phone.goto(f"{server.url}/web/login")
    phone.fill("input[name=user_id]", "admin-1")
    phone.fill("input[name=password]", demo_password("admin-1"))
    phone.click("button[type=submit]")
    phone.wait_for_url("**/web/admin")
    assert "Solicitudes en espera (1)" in phone.inner_text("main")
    _fits(phone)

    phone.click("text=Solicitudes en espera")
    phone.wait_for_url("**/web/admin/solicitudes")
    assert "Cliente sin prestamos" in phone.inner_text("main")
    _fits(phone)

    phone.click(f"form[action$='{disbursement_id}/aprobar'] button[type=submit]")
    phone.wait_for_url("**/web/resultado/**")
    assert "Solicitud aprobada" in phone.inner_text("main")
    _fits(phone)

    codes = [s.payload["code"] for s in server.notifier.delivered if "code" in s.payload]
    assert len(codes) == 1, "approving sends the client's code"
    confirmed = collector.post(
        f"/v1/disbursements/{disbursement_id}/confirm",
        json={"code": codes[0], "device_time": "2026-10-30T14:01:00+00:00"},
    )
    assert confirmed.status_code == 200 and confirmed.json()["status"] == "CONFIRMADO"

    phone.click("text=Continuar")
    phone.goto(f"{server.url}/web/admin/libro")
    assert "DESEMBOLSO" in phone.inner_text("main")
    _fits(phone)
