import pytest
from fastapi.testclient import TestClient
from support import FakeClock, Flow

from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.bootstrap import build_container


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def notifier() -> SimulatedNotifier:
    return SimulatedNotifier()


@pytest.fixture
def container(clock, notifier):
    return build_container(clock=clock, notifier=notifier)


@pytest.fixture
def api(container) -> TestClient:
    return TestClient(create_app(container))


@pytest.fixture
def flow(api, notifier) -> Flow:
    return Flow(api, notifier)
