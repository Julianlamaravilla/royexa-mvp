"""T6a: credentials and sessions live in PostgreSQL: a session survives a restart, the token
and the password are never stored in clear, and the application role cannot delete them.

Needs PostgreSQL: docker compose up -d --wait postgres, then uv run pytest -m postgres
"""

import os
from datetime import timedelta

import psycopg
import pytest
from database import reset_database
from fastapi.testclient import TestClient
from psycopg import errors
from support import COLLECTOR, FakeClock

from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.bootstrap import Settings, build_container
from royexa.migrate import MIGRATOR_URL
from royexa.seed import demo_password

pytestmark = pytest.mark.postgres

APP_URL = os.environ.get(
    "ROYEXA_LEDGER_URL", "postgresql://royexa_app:royexa_app@localhost:55432/royexa"
)


@pytest.fixture(autouse=True)
def clean_database():
    reset_database()
    yield
    reset_database()


def _server(clock: FakeClock) -> TestClient:
    built = build_container(Settings(ledger_url=APP_URL), clock, SimulatedNotifier())
    return TestClient(create_app(built))


def _login(client: TestClient, user: str = COLLECTOR) -> str:
    response = client.post(
        "/v1/auth/login", json={"user_id": user, "password": demo_password(user)}
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


def _owner(sql: str, params: tuple = ()):
    with psycopg.connect(MIGRATOR_URL) as connection:
        return connection.execute(sql, params).fetchall()


def test_t6a_a_session_survives_a_restart_and_a_revocation_stays_revoked():
    clock = FakeClock()
    first = _server(clock)
    kept, revoked = _login(first), _login(first)
    first.post("/v1/auth/logout", headers={"Authorization": f"Bearer {revoked}"})

    restarted = _server(clock)

    assert restarted.get("/v1/clients", headers={"Authorization": f"Bearer {kept}"}).status_code == 200
    assert restarted.get("/v1/clients", headers={"Authorization": f"Bearer {revoked}"}).status_code == 401


def test_t6a_a_session_still_expires_after_a_restart():
    clock = FakeClock()
    token = _login(_server(clock))
    clock.advance(timedelta(hours=12, seconds=1))

    restarted = _server(clock)

    assert restarted.get("/v1/clients", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_t6a_the_database_holds_a_digest_of_the_token_and_a_hash_of_the_password():
    token = _login(_server(FakeClock()))

    sessions = _owner("SELECT token_hash, user_id FROM session")
    credentials = dict(_owner("SELECT user_id, password_hash FROM credential"))

    assert [user for _, user in sessions] == [COLLECTOR]
    assert token not in sessions[0][0] and len(sessions[0][0]) == 64
    assert set(credentials) == {"cobrador-1", "cobrador-2", "admin-1", "admin-2"}
    assert all(value.startswith("scrypt$") for value in credentials.values())
    assert all(demo_password(user) not in value for user, value in credentials.items())


def test_t6a_seeding_again_keeps_the_credentials_it_already_had():
    _server(FakeClock())
    before = dict(_owner("SELECT user_id, password_hash FROM credential"))

    _server(FakeClock())

    assert dict(_owner("SELECT user_id, password_hash FROM credential")) == before


def test_t6a_the_application_role_cannot_delete_sessions_or_credentials():
    _login(_server(FakeClock()))

    with psycopg.connect(APP_URL) as app:
        for table in ("session", "credential"):
            with pytest.raises(errors.InsufficientPrivilege):
                app.execute(f"DELETE FROM {table}")
            app.rollback()
        with pytest.raises(errors.InsufficientPrivilege):
            app.execute("UPDATE credential SET password_hash = 'x'")
        app.rollback()
