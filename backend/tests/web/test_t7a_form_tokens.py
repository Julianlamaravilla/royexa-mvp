"""T7a, T7-P4: a form token is single-use, tied to the session that asked for it, and a
repeat returns the result already recorded. Runs on both adapters."""

from datetime import timedelta

import pytest
from support import ADMIN, COLLECTOR

from royexa.seed import demo_password
from royexa.web.forms import ClaimState, Outcome

PURPOSE = "pago"
DONE = Outcome("ok", "Pago registrado", "/web/ruta")


@pytest.fixture
def session_token(container):
    return container.authenticator.login(COLLECTOR, demo_password(COLLECTOR)).token


def test_t7a_a_fresh_token_is_accepted_once(container, session_token):
    tokens = container.form_tokens
    token = tokens.issue(session_token, PURPOSE)

    first = tokens.claim(token, session_token, PURPOSE)

    assert first.state is ClaimState.FRESH
    assert tokens.claim(token, session_token, PURPOSE).state is ClaimState.PENDING


def test_t7a_a_repeat_after_the_work_returns_the_recorded_result(container, session_token):
    tokens = container.form_tokens
    token = tokens.issue(session_token, PURPOSE)
    tokens.claim(token, session_token, PURPOSE)
    tokens.finish(token, DONE)

    repeat = tokens.claim(token, session_token, PURPOSE)

    assert repeat.state is ClaimState.REPLAY
    assert repeat.outcome == DONE


def test_t7a_a_repeat_while_the_first_is_still_working_is_told_so(container, session_token):
    tokens = container.form_tokens
    token = tokens.issue(session_token, PURPOSE)
    tokens.claim(token, session_token, PURPOSE)

    assert tokens.claim(token, session_token, PURPOSE).state is ClaimState.PENDING


def test_t7a_a_token_works_only_in_the_session_that_asked_for_it(container, session_token):
    tokens = container.form_tokens
    token = tokens.issue(session_token, PURPOSE)
    other = container.authenticator.login(ADMIN, demo_password(ADMIN)).token
    again = container.authenticator.login(COLLECTOR, demo_password(COLLECTOR)).token

    assert tokens.claim(token, other, PURPOSE).state is ClaimState.INVALID
    assert tokens.claim(token, again, PURPOSE).state is ClaimState.INVALID, "even the same user"
    assert tokens.claim(token, session_token, PURPOSE).state is ClaimState.FRESH


def test_t7a_a_token_is_for_one_purpose_only(container, session_token):
    tokens = container.form_tokens
    token = tokens.issue(session_token, PURPOSE)

    assert tokens.claim(token, session_token, "cierre").state is ClaimState.INVALID
    assert tokens.claim(token, session_token, PURPOSE).state is ClaimState.FRESH


@pytest.mark.parametrize("token", ["", "inventada", "x" * 500])
def test_t7a_an_unknown_token_is_invalid(container, session_token, token):
    assert container.form_tokens.claim(token, session_token, PURPOSE).state is ClaimState.INVALID


def test_t7a_each_issue_gives_a_different_token(container, session_token):
    tokens = container.form_tokens

    assert tokens.issue(session_token, PURPOSE) != tokens.issue(session_token, PURPOSE)


def test_t7a_only_the_session_that_asked_can_read_the_result(container, session_token):
    tokens = container.form_tokens
    token = tokens.issue(session_token, PURPOSE)
    tokens.claim(token, session_token, PURPOSE)
    tokens.finish(token, DONE)
    other = container.authenticator.login(ADMIN, demo_password(ADMIN)).token

    assert tokens.outcome_of(token, session_token) == DONE
    assert tokens.outcome_of(token, other) is None
    assert tokens.outcome_of("inventada", session_token) is None


def test_t7a_a_token_is_not_stored_in_clear(container, backend, session_token):
    if backend != "memory":
        pytest.skip("the database variant is in tests/postgres")
    token = container.form_tokens.issue(session_token, PURPOSE)

    rows = container.store.tables.form_tokens

    assert token not in rows
    assert all(token not in repr(row) for row in rows.values())


def test_t7a_a_token_dies_with_its_session(container, session_token, clock):
    tokens = container.form_tokens
    token = tokens.issue(session_token, PURPOSE)
    clock.advance(timedelta(hours=13))

    assert tokens.claim(token, session_token, PURPOSE).state is ClaimState.INVALID
