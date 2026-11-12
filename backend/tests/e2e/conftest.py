"""Fixtures of the browser tests (T7-P3): the app served from this process and a phone-sized
Chromium. Needs Chromium: `uv run playwright install chromium`, or ROYEXA_CHROMIUM with a
browser binary. CI sets ROYEXA_REQUIRE_E2E=1 so a missing browser fails there, not skips."""

import os
import socket
import threading
import time
from dataclasses import dataclass

import pytest
import uvicorn
from support import PHONE, FakeClock

from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.bootstrap import build_container

playwright_sync = pytest.importorskip("playwright.sync_api")


@dataclass(frozen=True)
class Server:
    url: str
    container: object
    notifier: SimulatedNotifier


@pytest.fixture
def server():
    notifier = SimulatedNotifier()
    container = build_container(clock=FakeClock(), notifier=notifier)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    config = uvicorn.Config(create_app(container), host="127.0.0.1", port=port, log_level="warning")
    running = uvicorn.Server(config)
    thread = threading.Thread(target=running.run, daemon=True)
    thread.start()
    while not running.started:
        time.sleep(0.05)
    yield Server(f"http://127.0.0.1:{port}", container, notifier)
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
