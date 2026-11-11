"""T2a: a registered client survives a restart of the server.

Needs PostgreSQL: docker compose up -d --wait postgres, then uv run pytest -m postgres
"""

import os

import pytest
from database import reset_database
from fastapi.testclient import TestClient
from support import ADMIN, COLLECTOR, FakeClock, Flow

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


def test_t2a_registered_client_is_still_there_after_a_restart():
    created = _server()._post(
        "/v1/clients", ADMIN, {"name": "Cliente persistente", "route_id": "ruta-2"}
    ).json()

    restarted = _server()

    assert restarted._get(f"/v1/clients/{created['id']}", COLLECTOR).json() == created
    listed = restarted._get("/v1/clients").json()
    assert [client["id"] for client in listed].count(created["id"]) == 1
    assert len(listed) == 5


def test_t2a_seeding_again_does_not_duplicate_the_demonstration_clients():
    _server()
    restarted = _server()

    assert len(restarted._get("/v1/clients").json()) == 4
