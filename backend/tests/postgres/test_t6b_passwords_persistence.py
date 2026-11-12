"""T6b: a changed password and a lock survive a restart, simultaneous failures are all
counted, and the strict mode refuses to start while demo passwords remain.

Needs PostgreSQL: docker compose up -d --wait postgres, then uv run pytest -m postgres
"""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import psycopg
import pytest
from database import reset_database
from fastapi.testclient import TestClient
from support import COLLECTOR, FakeClock

from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.bootstrap import Settings, build_container
from royexa.identity_access.domain import DemoPasswordsInUse
from royexa.migrate import MIGRATOR_URL
from royexa.seed import demo_password
from royexa.set_password import provision_password

pytestmark = pytest.mark.postgres

APP_URL = os.environ.get(
    "ROYEXA_LEDGER_URL", "postgresql://royexa_app:royexa_app@localhost:55432/royexa"
)
NEW = "una-clave-nueva-1234"
USERS = ("cobrador-1", "cobrador-2", "admin-1", "admin-2")


@pytest.fixture(autouse=True)
def clean_database():
    reset_database()
    yield
    reset_database()


def _container(clock: FakeClock | None = None, **settings):
    return build_container(
        Settings(ledger_url=APP_URL, **settings), clock or FakeClock(), SimulatedNotifier()
    )


def _server(clock: FakeClock | None = None, **settings) -> TestClient:
    return TestClient(create_app(_container(clock, **settings)))


def _login(client, user: str = COLLECTOR, password: str | None = None):
    return client.post(
        "/v1/auth/login", json={"user_id": user, "password": password or demo_password(user)}
    )


def _owner(sql: str, params: tuple = ()):
    with psycopg.connect(MIGRATOR_URL) as connection:
        return connection.execute(sql, params).fetchall()


def test_t6b_a_changed_password_survives_a_restart_and_clears_the_demo_mark():
    clock = FakeClock()
    first = _server(clock)
    token = _login(first).json()["token"]
    first.post(
        "/v1/auth/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": demo_password(COLLECTOR), "new_password": NEW},
    )

    restarted = _server(clock)

    assert _login(restarted, password=NEW).status_code == 200
    assert _login(restarted).status_code == 401
    assert _owner("SELECT is_demo FROM credential WHERE user_id = %s", (COLLECTOR,)) == [(False,)]
    assert _owner("SELECT count(*) FROM credential WHERE is_demo") == [(3,)]


def test_t6b_a_lock_survives_a_restart_and_lifts_on_time():
    clock = FakeClock()
    first = _server(clock)
    for _ in range(5):
        _login(first, password="clave-equivocada")

    restarted = _server(clock)
    assert _login(restarted).status_code == 401
    clock.advance(timedelta(minutes=15))

    assert _login(restarted).status_code == 200


def test_t6b_failures_that_arrive_together_are_all_counted():
    client = _server()
    start = Barrier(5)

    def fail(_: int):
        start.wait()
        return _login(client, password="clave-equivocada").status_code

    with ThreadPoolExecutor(max_workers=5) as pool:
        statuses = list(pool.map(fail, range(5)))

    assert statuses == [401] * 5
    assert _login(client).status_code == 401, "five at once still lock the user"


def test_t6b_strict_mode_seeds_no_demo_password_and_nobody_can_log_in():
    client = _server(require_changed_passwords=True)

    assert _owner("SELECT count(*) FROM credential") == [(0,)]
    assert _login(client).status_code == 401


def test_t6b_strict_mode_refuses_to_start_while_a_demo_password_remains():
    _container()  # an earlier start without the strict mode seeded the demo passwords

    with pytest.raises(DemoPasswordsInUse) as refused:
        _container(require_changed_passwords=True)

    message = str(refused.value)
    assert all(user in message for user in USERS)
    assert not any(demo_password(user) in message for user in USERS), "never prints a password"


def test_t6b_strict_mode_starts_once_every_password_was_provisioned():
    _container()
    for user in USERS:
        provision_password(APP_URL, user, f"clave-real-de-{user}")

    client = _server(require_changed_passwords=True)

    assert _login(client, "admin-1", "clave-real-de-admin-1").status_code == 200
    assert _login(client, "admin-1", demo_password("admin-1")).status_code == 401


def test_t6b_strict_mode_needs_a_database():
    with pytest.raises(DemoPasswordsInUse):
        build_container(Settings(require_changed_passwords=True), FakeClock(), SimulatedNotifier())


def test_t6b_provisioning_sets_the_password_on_a_user_without_one():
    _container(require_changed_passwords=True)

    provision_password(APP_URL, "cobrador-1", "clave-recien-puesta")

    assert _login(_server(), "cobrador-1", "clave-recien-puesta").status_code == 200


def test_t6b_provisioning_ends_the_sessions_and_the_lock_of_that_user():
    client = _server()
    token = _login(client).json()["token"]
    for _ in range(5):
        _login(client, password="clave-equivocada")

    provision_password(APP_URL, COLLECTOR, "clave-recien-puesta")

    assert client.get("/v1/clients", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert _login(client, password="clave-recien-puesta").status_code == 200


def test_t6b_provisioning_refuses_an_unknown_user_and_a_short_password():
    _container()

    with pytest.raises(ValueError, match="unknown user"):
        provision_password(APP_URL, "nadie", "clave-recien-puesta")
    with pytest.raises(ValueError, match="at least 12"):
        provision_password(APP_URL, COLLECTOR, "corta")
    assert _login(_server()).status_code == 200, "nothing changed"
