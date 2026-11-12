"""T6b, T6-P2 and T6-P3: change one's own password; lock a user after five failures.

Both adapters. Talks to the API directly. FakeClock starts on 2026-10-30 at 14:00 UTC.
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from support import ADMIN, COLLECTOR

from royexa.api import create_app
from royexa.seed import demo_password

NEW = "una-clave-nueva-1234"


def _client(container) -> TestClient:
    return TestClient(create_app(container))


def _login(client, user: str = COLLECTOR, password: str | None = None):
    return client.post(
        "/v1/auth/login", json={"user_id": user, "password": password or demo_password(user)}
    )


def _bearer(response) -> dict:
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _change(client, headers, current: str | None = None, new: str = NEW, user: str = COLLECTOR):
    return client.post(
        "/v1/auth/password",
        headers=headers,
        json={"current_password": current or demo_password(user), "new_password": new},
    )


def test_t6b_changing_the_password_replaces_it_for_the_next_login(container):
    client = _client(container)
    headers = _bearer(_login(client))

    response = _change(client, headers)

    assert response.status_code == 204
    assert _login(client, password=NEW).status_code == 200
    refused = _login(client, password=demo_password(COLLECTOR))
    assert refused.status_code == 401


def test_t6b_the_current_password_is_required_and_a_wrong_one_is_refused(container):
    client = _client(container)
    headers = _bearer(_login(client))

    wrong = _change(client, headers, current="no-es-la-clave-actual")

    assert wrong.status_code == 403
    assert wrong.json()["type"].endswith("/contrasena-actual-incorrecta")
    assert _login(client).status_code == 200, "nothing changed"
    missing = client.post("/v1/auth/password", headers=headers, json={"new_password": NEW})
    assert missing.status_code == 422


@pytest.mark.parametrize("new", ["", "corta-11-ch", "x" * 11])
def test_t6b_a_password_under_twelve_characters_is_refused(container, new):
    client = _client(container)
    headers = _bearer(_login(client))

    response = _change(client, headers, new=new)

    assert response.status_code == 422
    assert _login(client).status_code == 200


def test_t6b_exactly_twelve_characters_is_enough_and_a_very_long_one_is_not(container):
    client = _client(container)
    headers = _bearer(_login(client))

    assert _change(client, headers, new="x" * 257).status_code == 422
    assert _change(client, headers, new="doce-letras!").status_code == 204


def test_t6b_the_new_password_must_differ_from_the_current_one(container):
    client = _client(container)
    headers = _bearer(_login(client))

    response = _change(client, headers, new=demo_password(COLLECTOR))

    assert response.status_code == 422
    assert response.json()["type"].endswith("/contrasena-debil")


def test_t6b_changing_the_password_needs_a_session(container):
    response = _client(container).post(
        "/v1/auth/password",
        json={"current_password": demo_password(COLLECTOR), "new_password": NEW},
    )

    assert response.status_code == 401


def test_t6b_a_change_ends_the_other_sessions_of_that_user_and_only_theirs(container):
    client = _client(container)
    here = _bearer(_login(client))
    elsewhere = _bearer(_login(client))
    someone_else = _bearer(_login(client, ADMIN))

    _change(client, here)

    assert client.get("/v1/clients", headers=here).status_code == 200
    assert client.get("/v1/clients", headers=elsewhere).status_code == 401
    assert client.get("/v1/clients", headers=someone_else).status_code == 200


def test_t6b_five_failed_logins_lock_the_user_even_for_the_right_password(container):
    client = _client(container)
    for _ in range(5):
        assert _login(client, password="clave-equivocada").status_code == 401

    locked = _login(client)

    assert locked.status_code == 401
    assert locked.json() == _login(client, "nadie", "clave-equivocada").json(), (
        "a lock is not told apart from a wrong password or an unknown user"
    )


def test_t6b_four_failures_do_not_lock(container):
    client = _client(container)
    for _ in range(4):
        _login(client, password="clave-equivocada")

    assert _login(client).status_code == 200


def test_t6b_a_success_in_between_resets_the_count(container):
    client = _client(container)
    for _ in range(4):
        _login(client, password="clave-equivocada")
    assert _login(client).status_code == 200
    for _ in range(4):
        _login(client, password="clave-equivocada")

    assert _login(client).status_code == 200


def test_t6b_the_lock_lasts_fifteen_minutes_and_then_lifts(container, clock):
    client = _client(container)
    for _ in range(5):
        _login(client, password="clave-equivocada")

    clock.advance(timedelta(minutes=14, seconds=59))
    assert _login(client).status_code == 401
    clock.advance(timedelta(seconds=1))

    assert _login(client).status_code == 200


def test_t6b_a_lock_affects_that_user_only_and_leaves_their_sessions_alone(container):
    client = _client(container)
    open_session = _bearer(_login(client))
    for _ in range(5):
        _login(client, password="clave-equivocada")

    assert _login(client, ADMIN).status_code == 200
    assert client.get("/v1/clients", headers=open_session).status_code == 200


def test_t6b_failed_attempts_to_change_the_password_count_toward_the_lock(container):
    client = _client(container)
    headers = _bearer(_login(client))
    for _ in range(5):
        assert _change(client, headers, current="no-es-la-clave-actual").status_code == 403

    assert _login(client).status_code == 401
    assert _change(client, headers).status_code == 403, "locked: even the right one is refused"
