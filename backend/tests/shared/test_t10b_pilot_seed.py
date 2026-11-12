"""T10b1 (T10-P5): what a production start contains. ROYEXA_SEED=pilot loads the users and
routes of the pilot from a file and seeds no client, loan or password."""

import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from support import FakeClock

from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.bootstrap import Settings, build_container, ensure_production_ready
from royexa.identity_access.domain import Role
from royexa.seed import PILOT_DIRECTORY, load_directory


def test_t10b_the_pilot_file_describes_users_and_routes_with_their_limits():
    directory = load_directory(PILOT_DIRECTORY)

    users = {user.id: user for user in directory.users()}
    assert {u.id for u in users.values() if u.role is Role.ADMIN} == {"admin-1", "admin-2"}
    collector = users["cobrador-1"]
    assert collector.role is Role.COLLECTOR
    assert collector.disbursement_limit.cents > 0 and collector.opening_cash.cents > 0
    route = directory.route_of_collector("cobrador-1")
    assert route.max_disbursement >= collector.disbursement_limit and route.interest_bps > 0


def test_t10b_a_bad_file_is_refused_with_a_clear_message(tmp_path):
    broken = tmp_path / "directory.json"
    broken.write_text(json.dumps({"users": [{"id": "x", "name": "X", "role": "JEFE"}], "routes": []}))

    with pytest.raises(ValueError, match="role"):
        load_directory(broken)
    with pytest.raises(ValueError, match="does not exist"):
        load_directory(tmp_path / "nada.json")


def test_t10b_a_collector_without_a_route_is_refused(tmp_path):
    broken = tmp_path / "directory.json"
    broken.write_text(
        json.dumps(
            {
                "users": [
                    {"id": "c", "name": "C", "role": "COBRADOR", "disbursement_limit_cents": 1, "opening_cash_cents": 1}
                ],
                "routes": [],
            }
        )
    )

    with pytest.raises(ValueError, match="route"):
        load_directory(broken)


def test_t10b_the_pilot_start_has_no_clients_no_loans_and_no_demo_users():
    container = build_container(Settings(seed="pilot"), FakeClock(), SimulatedNotifier())

    assert container.client_queries.all() == []
    assert {u.id for u in container.directory.users()} == {
        u.id for u in load_directory(PILOT_DIRECTORY).users()
    }
    assert container.store.tables.loans == {} and container.store.tables.credentials == {}


def test_t10b_nobody_logs_in_to_a_pilot_start_until_a_password_is_set():
    container = build_container(Settings(seed="pilot"), FakeClock(), SimulatedNotifier())
    browser = TestClient(create_app(container))

    for password in ("demo-admin-1-royexa", "cualquiera-123456"):
        response = browser.post("/v1/auth/login", json={"user_id": "admin-1", "password": password})
        assert response.status_code == 401


def test_t10b_an_unknown_seed_or_a_missing_file_stops_the_start(monkeypatch, tmp_path):
    monkeypatch.setenv("ROYEXA_SEED", "produccion")
    with pytest.raises(ValueError, match="ROYEXA_SEED"):
        Settings.from_env()
    monkeypatch.setenv("ROYEXA_SEED", "pilot")
    monkeypatch.setenv("ROYEXA_DIRECTORY_FILE", str(tmp_path / "no-existe.json"))
    with pytest.raises(ValueError):
        build_container(Settings.from_env(), FakeClock(), SimulatedNotifier())


def test_t10b_demo_is_the_default_seed(monkeypatch):
    monkeypatch.delenv("ROYEXA_SEED", raising=False)

    assert Settings.from_env().seed == "demo"
    container = build_container(Settings(), FakeClock(), SimulatedNotifier())
    assert len(container.client_queries.all()) == 4


def test_t10b_the_strict_mode_refuses_the_known_password_of_the_application_role():
    settings = Settings(
        seed="pilot",
        require_changed_passwords=True,
        ledger_url="postgresql://royexa_app:royexa_app@db.example:5432/royexa",
    )

    with pytest.raises(Exception, match="royexa_app"):
        ensure_production_ready(settings)
    ensure_production_ready(replace(settings, ledger_url="postgresql://royexa_app:otra-clave-larga-1234@db:5432/royexa"))
    ensure_production_ready(replace(settings, require_changed_passwords=False))


def test_t10b_health_answers_ok_and_says_degraded_when_the_database_does_not(container):
    ok = TestClient(create_app(container)).get("/health")
    assert ok.status_code == 200 and ok.json() == {"status": "ok"}

    def broken() -> None:
        raise ConnectionError("the database is gone")

    down = TestClient(create_app(replace(container, ping=broken))).get("/health")
    assert down.status_code == 503 and down.json() == {"status": "degraded"}
