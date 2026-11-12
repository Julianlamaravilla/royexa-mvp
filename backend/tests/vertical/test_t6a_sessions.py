"""T6a, T6-P1: login, sessions and the end of the X-Actor-Id header. Runs on both adapters.

These tests talk to the API directly, without the Flow helper, so no session is added for
them. FakeClock starts on Friday 2026-10-30 at 14:00 UTC.
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from support import ADMIN, COLLECTOR

from royexa.api import create_app
from royexa.seed import demo_password


def _client(container) -> TestClient:
    """A client with an empty cookie jar."""
    return TestClient(create_app(container))


def _login(client: TestClient, user: str = COLLECTOR, password: str | None = None):
    return client.post(
        "/v1/auth/login",
        json={"user_id": user, "password": password or demo_password(user)},
    )


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_t6a_login_returns_a_bearer_token_that_lasts_twelve_hours(container, clock):
    client = _client(container)

    response = _login(client)

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["token_type"], body["user_id"], body["role"]) == ("Bearer", COLLECTOR, "COBRADOR")
    assert len(body["token"]) >= 43, "256 bits in base64url"
    assert body["expires_at"].startswith("2026-10-31T02:00:00"), "twelve hours after 14:00 UTC"
    assert client.get("/v1/clients", headers=_bearer(body["token"])).status_code == 200


def test_t6a_login_also_sets_an_http_only_same_site_cookie(container):
    client = _client(container)

    response = _login(client)

    cookie = response.headers["set-cookie"].lower()
    assert f"royexa_session={response.json()['token']}".lower() in cookie
    for attribute in ("httponly", "samesite=lax", "path=/", "max-age=43200"):
        assert attribute in cookie, attribute
    assert "secure" not in cookie, "plain HTTP in the tests; Secure is added under HTTPS"


def test_t6a_the_cookie_alone_opens_the_session_for_the_server_rendered_pages(container):
    client = _client(container)
    _login(client)  # the cookie jar now holds the session

    assert client.get("/v1/clients").status_code == 200


def test_t6a_wrong_password_and_unknown_user_look_the_same(container):
    client = _client(container)

    wrong = _login(client, COLLECTOR, "esta-no-es-la-clave")
    unknown = _login(client, "nadie", "esta-no-es-la-clave")

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.json()["type"].endswith("/credenciales-invalidas")
    assert "set-cookie" not in wrong.headers


def test_t6a_login_needs_both_fields(container):
    client = _client(container)

    assert client.post("/v1/auth/login", json={"user_id": COLLECTOR}).status_code == 422
    assert client.post("/v1/auth/login", json={"password": "x"}).status_code == 422
    assert client.post("/v1/auth/login", json={}).status_code == 422


PROTECTED = [
    ("GET", "/v1/clients"),
    ("GET", "/v1/ledger"),
    ("GET", "/v1/cash-boxes/cobrador-1"),
    ("GET", "/v1/loans/prestamo-impago"),
    ("GET", "/v1/routes/ruta-1/pending-visits"),
    ("POST", "/v1/disbursements"),
    ("POST", "/v1/notifications/dispatch"),
    ("POST", "/v1/loans/prestamo-impago/payments"),
    ("POST", "/v1/cash-boxes/cobrador-1/close"),
]


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_t6a_without_a_session_the_api_answers_401(container, method, path):
    response = _client(container).request(method, path, json={})

    assert response.status_code == 401
    assert response.json()["type"].endswith("/sesion-requerida")
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(("method", "path"), PROTECTED[:3])
def test_t6a_the_old_actor_header_no_longer_identifies_anyone(container, method, path):
    response = _client(container).request(method, path, headers={"X-Actor-Id": ADMIN}, json={})

    assert response.status_code == 401


def test_t6a_an_invalid_token_is_refused_and_does_not_fall_back_to_the_cookie(container):
    client = _client(container)
    _login(client)  # a valid cookie is in the jar

    response = client.get("/v1/clients", headers=_bearer("no-es-un-token"))

    assert response.status_code == 401


def test_t6a_the_session_expires_twelve_hours_after_the_login(container, clock):
    client = _client(container)
    token = _login(client).json()["token"]

    clock.advance(timedelta(hours=11, minutes=59))
    assert client.get("/v1/clients", headers=_bearer(token)).status_code == 200

    clock.advance(timedelta(minutes=2))
    expired = client.get("/v1/clients", headers=_bearer(token))
    assert expired.status_code == 401
    assert expired.json()["type"].endswith("/sesion-requerida")


def test_t6a_logout_revokes_that_session_at_once_and_only_that_one(container):
    client = _client(container)
    first = _login(client).json()["token"]
    second = _login(client).json()["token"]
    assert first != second, "several sessions per user"

    response = client.post("/v1/auth/logout", headers=_bearer(first))

    assert response.status_code == 204
    assert client.get("/v1/clients", headers=_bearer(first)).status_code == 401
    assert client.get("/v1/clients", headers=_bearer(second)).status_code == 200


def test_t6a_logout_clears_the_cookie(container):
    client = _client(container)
    _login(client)

    response = client.post("/v1/auth/logout")

    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()
    assert client.get("/v1/clients").status_code == 401


def test_t6a_logout_needs_a_session_and_a_second_one_is_refused(container):
    client = _client(container)
    token = _login(client).json()["token"]

    assert _client(container).post("/v1/auth/logout").status_code == 401
    assert client.post("/v1/auth/logout", headers=_bearer(token)).status_code == 204
    assert client.post("/v1/auth/logout", headers=_bearer(token)).status_code == 401


def test_t6a_each_session_acts_as_its_own_user(container):
    client = _client(container)
    collector = _login(client, COLLECTOR).json()["token"]
    admin = _login(client, ADMIN).json()["token"]

    assert client.get("/v1/ledger", headers=_bearer(collector)).status_code == 403
    assert client.get("/v1/ledger", headers=_bearer(admin)).status_code == 200


def test_t6a_a_user_cannot_use_the_session_of_another_by_naming_them(container):
    client = _client(container)
    token = _login(client, COLLECTOR).json()["token"]
    headers = {**_bearer(token), "X-Actor-Id": ADMIN}

    assert client.get("/v1/ledger", headers=headers).status_code == 403


def test_t6a_neither_the_token_nor_the_password_is_kept_in_clear(container, backend):
    if backend != "memory":
        pytest.skip("the database variant is in tests/postgres")
    client = _client(container)
    token = _login(client).json()["token"]

    tables = container.store.tables
    assert token not in tables.sessions, "the key is a digest of the token"
    assert all(token not in repr(row) for row in tables.sessions.values())
    stored = tables.credentials[COLLECTOR].password_hash
    assert demo_password(COLLECTOR) not in stored
    assert stored.startswith("scrypt$")
