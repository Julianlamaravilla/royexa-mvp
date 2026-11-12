"""T5d: the correction survives a restart, the database refuses a malformed one, and the
migrations still apply once an adjustment exists (they are reapplied on every start).

Needs PostgreSQL: docker compose up -d --wait postgres, then uv run pytest -m postgres
"""

import os
from uuid import uuid4

import psycopg
import pytest
from database import reset_database
from fastapi.testclient import TestClient
from psycopg import errors
from support import ADMIN, COLLECTOR, FakeClock, Flow

from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.bootstrap import Settings, build_container
from royexa.migrate import apply_migrations

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


def _original(flow: Flow) -> dict:
    loan = flow.confirmed(client="cliente-1")["loan"]
    payment = flow.pay(loan["id"], 30_000).json()["payment"]
    return flow.payment_entry(payment["id"])


def test_t5d_the_adjustment_and_its_untouched_original_survive_a_restart():
    clock = FakeClock()
    flow = _server(clock)
    original = _original(flow)
    adjustment = flow.adjust(original["id"], -2_500).json()

    restarted = _server(clock)

    entries = {entry["id"]: entry for entry in restarted.ledger()}
    assert entries[original["id"]] == original
    assert entries[adjustment["id"]] == adjustment
    box = restarted._get(f"/v1/cash-boxes/{COLLECTOR}", ADMIN).json()
    assert box["balance_cents"] == 100_000_000 - 100_000 + 30_000 - 2_500


def test_t5d_the_migrations_apply_again_while_an_adjustment_exists():
    """006 used to re-add the old ledger checks on every start, which a row of the new
    type violates."""
    flow = _server(FakeClock())
    flow.adjust(_original(flow)["id"], -2_500)

    assert apply_migrations()[-1].endswith(".sql")
    assert apply_migrations()[-1].endswith(".sql")
    assert [e["entry_type"] for e in flow.ledger()].count("AJUSTE") == 1


def _insert(entry_type: str, **columns) -> None:
    values = {
        "id": str(uuid4()),
        "entry_type": entry_type,
        "amount_cents": -100,
        "cash_box_id": "caja-x",
        "actor_id": "admin-1",
        "device_time": "2026-10-30T14:00:00+00:00",
        "server_time": "2026-10-30T14:00:00+00:00",
        **columns,
    }
    names = ", ".join(values)
    marks = ", ".join(["%s"] * len(values))
    with psycopg.connect(APP_URL) as connection:
        connection.execute(f"INSERT INTO ledger_entry ({names}) VALUES ({marks})", list(values.values()))


@pytest.mark.parametrize(
    "columns",
    [
        {"reason": "falta el original"},  # no adjusts_entry_id
        {"adjusts_entry_id": "x", "reason": None},  # no motive
        {"adjusts_entry_id": "x", "reason": "  "},  # blank motive
        {"adjusts_entry_id": "x", "reason": "r", "disbursement_id": "d-1"},  # two operations
        {"adjusts_entry_id": "x", "reason": "r", "amount_cents": 0},  # never zero
    ],
)
def test_t5d_the_database_refuses_a_malformed_adjustment(columns):
    flow = _server(FakeClock())
    original = _original(flow)
    if columns.get("adjusts_entry_id") == "x":
        columns = {**columns, "adjusts_entry_id": original["id"]}

    with pytest.raises((errors.CheckViolation, errors.ForeignKeyViolation)):
        _insert("AJUSTE", **columns)


def test_t5d_a_negative_amount_is_only_for_an_adjustment():
    flow = _server(FakeClock())
    original = _original(flow)

    with pytest.raises(errors.CheckViolation):
        _insert("PAGO", payment_id="p-x", payment_method="EFECTIVO", amount_cents=-100)
    with pytest.raises(errors.CheckViolation):
        _insert("DESEMBOLSO", disbursement_id="d-x", amount_cents=-100)
    assert original["entry_type"] == "PAGO"
