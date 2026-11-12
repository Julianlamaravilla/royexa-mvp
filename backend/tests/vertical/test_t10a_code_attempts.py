"""T10a (T10-P3): five wrong codes in a row lock the request for 15 minutes. The correct code
is refused while it lasts; the lock ends by itself. Runs on both adapters."""

from datetime import timedelta

import pytest


@pytest.fixture
def approved(flow):
    disbursement = flow.approved()
    return disbursement["id"], flow.issued_code(disbursement["id"])


def _wrong(flow, disbursement_id: str, times: int) -> list[str]:
    return [
        flow.confirm(disbursement_id, f"MAL{n}").json()["type"].rsplit("/", 1)[1]
        for n in range(times)
    ]


def test_t10a_the_first_four_wrong_codes_are_plain_refusals(flow, approved):
    disbursement_id, _ = approved

    assert _wrong(flow, disbursement_id, 4) == ["codigo-invalido"] * 4


def test_t10a_the_fifth_wrong_code_locks_the_request_and_says_so(flow, approved):
    disbursement_id, _ = approved

    kinds = _wrong(flow, disbursement_id, 5)

    assert kinds == ["codigo-invalido"] * 4 + ["codigo-bloqueado"]


def test_t10a_while_locked_even_the_correct_code_is_refused_and_no_money_moves(flow, approved):
    disbursement_id, code = approved
    before = flow.cash_balance()
    _wrong(flow, disbursement_id, 5)

    response = flow.confirm(disbursement_id, code)

    assert response.status_code == 423 and response.json()["type"].endswith("/codigo-bloqueado")
    assert flow.read(disbursement_id)["status"] == "APROBADO" and flow.cash_balance() == before


def test_t10a_wrong_codes_during_the_lock_do_not_extend_it(flow, approved, clock):
    disbursement_id, code = approved
    _wrong(flow, disbursement_id, 5)
    clock.advance(timedelta(minutes=14))
    assert flow.confirm(disbursement_id, "OTRO").status_code == 423

    clock.advance(timedelta(minutes=1, seconds=1))

    assert flow.confirm(disbursement_id, code).status_code == 200


def test_t10a_after_fifteen_minutes_the_correct_code_confirms(flow, approved, clock):
    disbursement_id, code = approved
    _wrong(flow, disbursement_id, 5)
    clock.advance(timedelta(minutes=15))

    response = flow.confirm(disbursement_id, code)

    assert response.status_code == 200 and response.json()["status"] == "CONFIRMADO"


def test_t10a_after_a_lock_the_count_starts_again_from_zero(flow, approved, clock):
    disbursement_id, _ = approved
    _wrong(flow, disbursement_id, 5)
    clock.advance(timedelta(minutes=15))

    assert _wrong(flow, disbursement_id, 4) == ["codigo-invalido"] * 4


def test_t10a_a_correct_code_resets_the_count_only_when_it_confirms(flow, approved):
    disbursement_id, code = approved
    _wrong(flow, disbursement_id, 4)

    assert flow.confirm(disbursement_id, code).status_code == 200
    assert flow.confirm(disbursement_id, code).status_code == 200, "the replay is not locked"
    assert flow.confirm(disbursement_id, "MAL").status_code == 422, "nor counted"


def test_t10a_the_lock_is_of_one_request_not_of_the_collector(flow, approved):
    disbursement_id, _ = approved
    _wrong(flow, disbursement_id, 5)
    other = flow.approved(client="cliente-3")
    other_code = flow.issued_code(other["id"])

    assert flow.confirm(other["id"], other_code).status_code == 200


def test_t10a_a_locked_request_shows_its_state_in_the_audit_trail(flow, approved):
    disbursement_id, _ = approved
    _wrong(flow, disbursement_id, 5)

    stored = flow.read(disbursement_id)

    assert stored["failed_code_attempts"] == 0 and stored["code_locked_until"] is not None
