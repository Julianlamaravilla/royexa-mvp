"""T4: a receipt waiting in the outbox survives a restart and is delivered afterwards.

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


def _server() -> tuple[Flow, SimulatedNotifier]:
    notifier = SimulatedNotifier()
    built = build_container(Settings(ledger_url=APP_URL), FakeClock(), notifier)
    return Flow(TestClient(create_app(built)), notifier), notifier


def test_t4_pending_receipt_survives_a_restart_and_is_then_delivered_with_its_payload():
    flow, _ = _server()
    payment = flow.pay("prestamo-impago", 20_000).json()["payment"]

    restarted, notifier = _server()
    queued = restarted._get(f"/v1/notifications?payment_id={payment['id']}", ADMIN).json()
    assert [(n["kind"], n["status"]) for n in queued] == [("COMPROBANTE_PAGO", "PENDIENTE")]
    restarted.dispatch()

    sent = [n for n in notifier.delivered if n.payment_id == payment["id"]]
    assert [n.payload for n in sent] == [
        {"amount_cents": "20000", "outstanding_cents": "50000", "next_due_date": "2026-09-01"}
    ]
    sent_notice = restarted._get(f"/v1/notifications?payment_id={payment['id']}", ADMIN).json()
    assert [n["status"] for n in sent_notice] == ["ENVIADO"]
