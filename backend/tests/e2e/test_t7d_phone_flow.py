"""T7d (T7-P3): a real browser at 360 px walks the collector's day: login, a payment and the
close of the box, with no horizontal scroll on any page. The server and the browser come from
conftest.py (Friday 2026-10-30, in-memory adapters)."""

from support import assert_fits_phone as _fits
from royexa.seed import demo_password


def test_t7d_login_payment_and_close_fit_a_360_px_phone(server, phone):
    phone.goto(f"{server.url}/web/")
    assert phone.url.endswith("/web/login")
    _fits(phone)

    phone.fill("input[name=user_id]", "cobrador-1")
    phone.fill("input[name=password]", demo_password("cobrador-1"))
    phone.click("button[type=submit]")
    phone.wait_for_url("**/web/ruta")
    assert "Pendientes (1)" in phone.inner_text("main")
    _fits(phone)

    phone.click("text=Registrar pago")
    phone.wait_for_url("**/web/pago/**")
    _fits(phone)
    phone.fill("input[name=monto]", "700,00")
    phone.select_option("select[name=medio]", "EFECTIVO")
    phone.click("button[type=submit]")
    phone.wait_for_url("**/web/resultado/**")
    assert "Pago de 700,00 registrado" in phone.inner_text("main")
    _fits(phone)

    phone.click("text=Continuar")
    phone.wait_for_url("**/web/ruta")
    assert "Pagaron (1)" in phone.inner_text("main")
    _fits(phone)

    phone.click("text=Cerrar caja")
    phone.wait_for_url("**/web/cierre")
    _fits(phone)
    phone.fill("input[name=entregado]", "650,50")
    phone.click("button[type=submit]")
    phone.wait_for_url("**/web/resultado/**")
    text = phone.inner_text("main")
    assert "Caja cerrada" in text and "Faltan 49,50" in text
    _fits(phone)

    phone.click("text=Continuar")
    phone.wait_for_url("**/web/ruta")
    assert "Caja cerrada" in phone.inner_text("main")
    _fits(phone)


def test_t7d_a_second_tap_on_the_payment_button_sends_the_form_once(server, phone):
    phone.goto(f"{server.url}/web/login")
    phone.fill("input[name=user_id]", "cobrador-1")
    phone.fill("input[name=password]", demo_password("cobrador-1"))
    phone.click("button[type=submit]")
    phone.wait_for_url("**/web/ruta")
    phone.click("text=Registrar pago")
    phone.fill("input[name=monto]", "100,00")

    phone.dblclick("button[type=submit]")
    phone.wait_for_url("**/web/resultado/**")

    assert "Pago de 100,00 registrado" in phone.inner_text("main")
    phone.click("text=Continuar")
    phone.wait_for_url("**/web/ruta")
    assert "Pagaron (1)" in phone.inner_text("main")
