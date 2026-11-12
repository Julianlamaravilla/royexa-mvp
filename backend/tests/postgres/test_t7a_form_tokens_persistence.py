"""T7a: a form token survives a restart, only one of two simultaneous claims wins, and the
database keeps a digest, never the token.

Needs PostgreSQL: docker compose up -d --wait postgres, then uv run pytest -m postgres
"""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import psycopg
import pytest
from database import reset_database
from psycopg import errors
from support import COLLECTOR, FakeClock

from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.bootstrap import Settings, build_container
from royexa.migrate import MIGRATOR_URL
from royexa.seed import demo_password
from royexa.web.forms import ClaimState, Outcome

pytestmark = pytest.mark.postgres

APP_URL = os.environ.get(
    "ROYEXA_LEDGER_URL", "postgresql://royexa_app:royexa_app@localhost:55432/royexa"
)
DONE = Outcome("ok", "Pago registrado", "/web/ruta")


@pytest.fixture(autouse=True)
def clean_database():
    reset_database()
    yield
    reset_database()


def _container(clock: FakeClock):
    return build_container(Settings(ledger_url=APP_URL), clock, SimulatedNotifier())


def test_t7a_a_token_and_its_result_survive_a_restart():
    clock = FakeClock()
    first = _container(clock)
    session = first.authenticator.login(COLLECTOR, demo_password(COLLECTOR)).token
    token = first.form_tokens.issue(session, "pago")
    first.form_tokens.claim(token, session, "pago")
    first.form_tokens.finish(token, DONE)

    restarted = _container(clock)

    repeat = restarted.form_tokens.claim(token, session, "pago")
    assert (repeat.state, repeat.outcome) == (ClaimState.REPLAY, DONE)


def test_t7a_of_two_simultaneous_claims_exactly_one_is_fresh():
    container = _container(FakeClock())
    session = container.authenticator.login(COLLECTOR, demo_password(COLLECTOR)).token
    token = container.form_tokens.issue(session, "pago")
    start = Barrier(4)

    def claim(_: int):
        start.wait()
        return container.form_tokens.claim(token, session, "pago").state

    with ThreadPoolExecutor(max_workers=4) as pool:
        states = list(pool.map(claim, range(4)))

    assert states.count(ClaimState.FRESH) == 1
    assert set(states) <= {ClaimState.FRESH, ClaimState.PENDING}


def test_t7a_the_database_keeps_a_digest_of_the_token_and_never_deletes_it():
    container = _container(FakeClock())
    session = container.authenticator.login(COLLECTOR, demo_password(COLLECTOR)).token
    token = container.form_tokens.issue(session, "pago")

    with psycopg.connect(MIGRATOR_URL) as owner:
        stored = owner.execute("SELECT token_hash, purpose FROM form_token").fetchall()
    assert [purpose for _, purpose in stored] == ["pago"]
    assert token not in stored[0][0] and len(stored[0][0]) == 64
    with psycopg.connect(APP_URL) as app, pytest.raises(errors.InsufficientPrivilege):
        app.execute("DELETE FROM form_token")
