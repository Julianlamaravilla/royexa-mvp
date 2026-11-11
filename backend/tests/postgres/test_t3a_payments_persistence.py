"""T3a: payments, their ledger entry and the loan balance survive a restart, and two
simultaneous payments never overwrite each other.

Needs PostgreSQL: docker compose up -d --wait postgres, then uv run pytest -m postgres
"""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from database import reset_database
from fastapi.testclient import TestClient
from support import COLLECTOR, FakeClock, Flow

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


def test_t3a_payment_balance_ledger_entry_and_box_survive_a_restart():
    flow = _server()
    loan = flow.confirmed()["loan"]
    before = flow.cash_balance()
    payment = flow.pay(loan["id"], 3_000).json()["payment"]

    restarted = _server()

    stored = restarted._get(f"/v1/loans/{loan['id']}").json()
    assert (stored["remaining_installments"], stored["outstanding_cents"]) == ("19.5", 117_000)
    assert restarted._get(f"/v1/loans/{loan['id']}/payments").json() == [payment]
    assert restarted.cash_balance() == before + 3_000
    entries = [e for e in restarted.ledger() if e["entry_type"] == "PAGO"]
    assert [(e["payment_id"], e["cash_effect_cents"]) for e in entries] == [(payment["id"], 3_000)]


def test_t3a_two_simultaneous_payments_on_one_loan_never_lose_an_update():
    flow = _server()
    loan = flow.confirmed()["loan"]
    start = Barrier(2)

    def pay(_: int):
        start.wait()
        return flow.pay(loan["id"], 1_000)

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = [response.status_code for response in pool.map(pay, range(2))]

    assert set(statuses) <= {201, 409}
    assert 201 in statuses
    accepted = statuses.count(201)
    stored = flow._get(f"/v1/loans/{loan['id']}").json()
    assert stored["outstanding_cents"] == 120_000 - 1_000 * accepted
    assert len(flow._get(f"/v1/loans/{loan['id']}/payments", COLLECTOR).json()) == accepted
