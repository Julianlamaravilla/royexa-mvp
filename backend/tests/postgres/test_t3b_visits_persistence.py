"""T3b: a non-payment survives a restart and keeps the client out of the pending list.

Needs PostgreSQL: docker compose up -d --wait postgres, then uv run pytest -m postgres
"""

import os

import pytest
from database import reset_database
from fastapi.testclient import TestClient
from support import ADMIN, FakeClock, Flow

from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.bootstrap import Settings, build_container

pytestmark = pytest.mark.postgres

APP_URL = os.environ.get(
    "ROYEXA_LEDGER_URL", "postgresql://royexa_app:royexa_app@localhost:55432/royexa"
)


@pytest.fixture(autouse=True)
def clean_database():
    reset_database()
    yield
    reset_database()


def _server() -> Flow:
    built = build_container(Settings(ledger_url=APP_URL), FakeClock(), SimulatedNotifier())
    return Flow(TestClient(create_app(built)), built.notifier)


def test_t3b_non_payment_and_its_effect_on_the_pending_list_survive_a_restart():
    flow = _server()
    assert flow.pending_clients() == ["cliente-2"]
    registered = flow.non_pay("prestamo-impago", "no tiene dinero", "2026-11-02").json()

    restarted = _server()

    assert restarted._get("/v1/loans/prestamo-impago/non-payments", ADMIN).json() == [registered]
    assert restarted.pending_clients() == []
    assert restarted._get("/v1/loans/prestamo-impago").json()["outstanding_cents"] == 70_000
