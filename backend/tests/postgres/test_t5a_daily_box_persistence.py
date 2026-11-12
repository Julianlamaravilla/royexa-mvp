"""T5a: the box of the day survives a restart, is unique per collector and day, and two
first movements of a day open one box only.

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
from royexa.cash_box.domain import CashBox
from royexa.shared.errors import StaleWrite
from royexa.shared.money import Money

pytestmark = pytest.mark.postgres

APP_URL = os.environ.get(
    "ROYEXA_LEDGER_URL", "postgresql://royexa_app:royexa_app@localhost:55432/royexa"
)
FLOAT = 100_000_000


@pytest.fixture(autouse=True)
def clean_database():
    reset_database()
    yield
    reset_database()


def _server(clock: FakeClock) -> Flow:
    built = build_container(Settings(ledger_url=APP_URL), clock, SimulatedNotifier())
    return Flow(TestClient(create_app(built)), built.notifier)


def _box(flow: Flow, day: str | None = None) -> dict:
    suffix = f"?date={day}" if day else ""
    return flow._get(f"/v1/cash-boxes/{COLLECTOR}{suffix}").json()


def test_t5a_the_box_of_the_day_and_the_next_one_survive_a_restart():
    clock = FakeClock()
    flow = _server(clock)
    flow.confirmed()
    clock.advance(timedelta(days=1))

    restarted = _server(clock)

    assert _box(restarted, "2026-10-30")["balance_cents"] == FLOAT - 100_000
    fresh = _box(restarted)
    assert (fresh["day"], fresh["balance_cents"]) == ("2026-10-31", FLOAT)


def test_t5a_a_collector_has_one_box_per_day_in_the_database():
    day = date(2026, 10, 30)
    first = PostgresSession(APP_URL)
    first.cash.save(CashBox("caja-a", "cobrador-9", day, Money(500), Money(500)))
    first.commit()

    second = PostgresSession(APP_URL)
    with pytest.raises(StaleWrite):
        second.cash.save(CashBox("caja-b", "cobrador-9", day, Money(500), Money(500)))
    second.rollback()

    other_day = PostgresSession(APP_URL)
    other_day.cash.save(CashBox("caja-c", "cobrador-9", date(2026, 10, 31), Money(500), Money(500)))
    other_day.commit()


def test_t5a_two_first_movements_of_a_day_open_a_single_box():
    clock = FakeClock()
    flow = _server(clock)
    loan = flow.confirmed()["loan"]
    clock.advance(timedelta(days=1))  # no box exists yet for Saturday
    start = Barrier(2)

    def pay(_: int):
        start.wait()
        return flow.pay(loan["id"], 1_000)

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = [response.status_code for response in pool.map(pay, range(2))]

    assert set(statuses) <= {201, 409}
    assert 201 in statuses
    saturday = _box(flow)
    assert saturday["id"] == "caja-cobrador-1-2026-10-31"
    assert saturday["balance_cents"] == FLOAT + 1_000 * statuses.count(201)
