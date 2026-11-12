"""T5b: the close survives a restart, a box closes once, and a payment racing the close
never slips in unseen.

Needs PostgreSQL: docker compose up -d --wait postgres, then uv run pytest -m postgres
"""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier

import pytest
from database import reset_database
from fastapi.testclient import TestClient
from support import COLLECTOR, FakeClock, Flow

from royexa.adapters.postgres_state import PostgresSession
from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.bootstrap import Settings, build_container
from royexa.cash_box.domain import CashClose
from royexa.shared.errors import StaleWrite
from royexa.shared.money import Money

pytestmark = pytest.mark.postgres

APP_URL = os.environ.get(
    "ROYEXA_LEDGER_URL", "postgresql://royexa_app:royexa_app@localhost:55432/royexa"
)


@pytest.fixture(autouse=True)
def clean_database():
    reset_database()
    yield
    reset_database()


def _server(clock: FakeClock) -> Flow:
    built = build_container(Settings(ledger_url=APP_URL), clock, SimulatedNotifier())
    return Flow(TestClient(create_app(built)), built.notifier)


def _loan_from_yesterday(flow: Flow, clock: FakeClock) -> dict:
    clock.advance(-timedelta(days=1))
    loan = flow.confirmed(client="cliente-1")["loan"]
    clock.advance(timedelta(days=1))
    return loan


def test_t5b_the_close_and_the_closed_box_survive_a_restart():
    clock = FakeClock()
    flow = _server(clock)
    loan = _loan_from_yesterday(flow, clock)
    flow.pay(loan["id"], 75_000)
    flow.visit_everyone()
    closed = flow.close_box(72_500).json()

    restarted = _server(clock)

    assert restarted.cash_closes().json() == [closed]
    box = restarted._get(f"/v1/cash-boxes/{COLLECTOR}").json()
    assert box["closed"] is True
    assert restarted.pay(loan["id"], 1_000).status_code == 409


def test_t5b_the_database_holds_one_close_per_box():
    clock = FakeClock()
    flow = _server(clock)
    flow.visit_everyone()
    closed = flow.close_box(0).json()
    duplicate = CashClose(
        "otro-cierre",
        closed["cash_box_id"],
        COLLECTOR,
        date(2026, 10, 30),
        Money(0),
        Money(0),
        COLLECTOR,
        clock.now(),
        clock.now(),
    )

    session = PostgresSession(APP_URL)
    with pytest.raises(StaleWrite):
        session.cash_closes.add(duplicate)
    session.rollback()


def test_t5b_a_payment_racing_the_close_is_either_counted_in_it_or_refused():
    clock = FakeClock()
    flow = _server(clock)
    loan = _loan_from_yesterday(flow, clock)
    flow.pay(loan["id"], 10_000)
    flow.visit_everyone()
    start = Barrier(2)

    def race(which: int):
        start.wait()
        if which == 0:
            return "close", flow.close_box(10_000)
        return "pay", flow.pay(loan["id"], 5_000)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = dict(pool.map(race, range(2)))

    closes = flow.cash_closes().json()
    cash_in = sum(
        e["cash_effect_cents"]
        for e in flow.ledger()
        if e["entry_type"] == "PAGO" and e["cash_box_id"].endswith("2026-10-30")
    )
    if outcomes["close"].status_code == 201:
        assert closes[0]["expected_cents"] == cash_in, "nothing slipped in after the count"
        assert outcomes["pay"].status_code in (201, 409)
    else:
        assert outcomes["close"].status_code == 409
        assert closes == []
    assert outcomes["pay"].status_code in (201, 409)
