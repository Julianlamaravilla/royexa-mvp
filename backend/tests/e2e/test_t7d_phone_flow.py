"""T7d (T7-P3): a real browser at 360 px walks the collector's day: login, a payment and the
close of the box, with no horizontal scroll on any page.

The server runs in this process on a free port with the in-memory adapters and the test
clock (Friday 2026-10-30), so the flow does not depend on the day the suite runs. Needs
Chromium: `uv run playwright install chromium`, or ROYEXA_CHROMIUM with a browser binary.
CI sets ROYEXA_REQUIRE_E2E=1 so a missing browser fails there instead of skipping.
"""

import os
import socket
import threading
import time

import pytest
import uvicorn
from support import FakeClock

from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.bootstrap import build_container
from royexa.seed import demo_password

playwright_sync = pytest.importorskip("playwright.sync_api")

PHONE = {"width": 360, "height": 740}


@pytest.fixture
def server():
    container = build_container(clock=FakeClock(), notifier=SimulatedNotifier())
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    config = uvicorn.Config(create_app(container), host="127.0.0.1", port=port, log_level="warning")
    running = uvicorn.Server(config)
    thread = threading.Thread(target=running.run, daemon=True)
    thread.start()
    while not running.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    running.should_exit = True
    thread.join(timeout=10)


@pytest.fixture
def phone():
    with playwright_sync.sync_playwright() as driver:
        executable = os.environ.get("ROYEXA_CHROMIUM") or None
        try:
            browser = driver.chromium.launch(executable_path=executable)
        except playwright_sync.Error as error:
            if os.environ.get("ROYEXA_REQUIRE_E2E"):
                raise
            pytest.skip(f"no Chromium to drive: {str(error).splitlines()[0]}")
        page = browser.new_context(viewport=PHONE, locale="es").new_page()
        yield page
        browser.close()


def _fits(page) -> None:
    widths = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    assert widths[0] <= widths[1] == PHONE["width"], f"horizontal scroll on {page.url}: {widths}"


def test_t7d_login_payment_and_close_fit_a_360_px_phone(server, phone):
    phone.goto(f"{server}/web/")
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
    phone.goto(f"{server}/web/login")
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
