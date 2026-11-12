import os

# A cheap scrypt cost keeps the logins of hundreds of tests fast; the hash records its cost,
# and a test checks that a clean environment keeps the strong default. Set before royexa loads.
os.environ.setdefault("ROYEXA_SCRYPT_N", "16")

import pytest  # noqa: E402
from database import reset_database
from fastapi.testclient import TestClient
from support import FakeClock, Flow

from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.bootstrap import Settings, build_container


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def notifier() -> SimulatedNotifier:
    return SimulatedNotifier()


DATABASE_URL = os.environ.get(
    "ROYEXA_LEDGER_URL", "postgresql://royexa_app:royexa_app@localhost:55432/royexa"
)


@pytest.fixture(params=["memory", pytest.param("postgres", marks=pytest.mark.postgres)])
def backend(request) -> str:
    """T1b: the vertical tests run on both adapters; the PostgreSQL run needs the database."""
    return request.param


@pytest.fixture
def container(backend, clock, notifier):
    if backend == "memory":
        yield build_container(clock=clock, notifier=notifier)
        return
    reset_database()
    yield build_container(Settings(ledger_url=DATABASE_URL), clock, notifier)
    reset_database()


@pytest.fixture
def api(container) -> TestClient:
    return TestClient(create_app(container))


@pytest.fixture
def flow(api, notifier) -> Flow:
    return Flow(api, notifier)
