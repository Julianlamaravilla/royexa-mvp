"""PR-11, guards of the confirmation code over the API. UC-03. RN-03, CA-05, CA-06, INV-02."""

from datetime import timedelta

import pytest
from support import ADMIN, COLLECTOR

OTHER_COLLECTOR = "cobrador-2"
OTHER_CLIENT = "cliente-3"
WRONG_CODE = "NOTACODE"


def test_pr11_wrong_code_moves_nothing_and_the_valid_code_still_works(flow):
    """PR-11 / RN-03 / CA-05: a failed attempt spends neither the money nor the code."""
    opening_balance = flow.cash_balance()
    disbursement = flow.approved()
    code = flow.issued_code(disbursement["id"])

    response = flow.confirm(disbursement["id"], WRONG_CODE)

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"].endswith("/codigo-invalido")
    read = flow.read(disbursement["id"])
    assert read["status"] == "APROBADO"
    assert read["loan"] is None
    assert flow.ledger(disbursement["id"]) == []
    assert flow.cash_balance() == opening_balance

    assert flow.confirm(disbursement["id"], code).json()["status"] == "CONFIRMADO"
    assert len(flow.ledger(disbursement["id"])) == 1
    assert flow.cash_balance() == opening_balance - disbursement["amount_cents"]


def test_pr11_code_of_another_operation_is_refused(flow):
    """PR-11 / RN-03: a code belongs to one operation and one client."""
    opening_balance = flow.cash_balance()
    first = flow.approved()
    other = flow.approved(client=OTHER_CLIENT)
    first_code = flow.issued_code(first["id"])
    flow.issued_code(other["id"])

    response = flow.confirm(other["id"], first_code)

    assert response.status_code == 422
    assert response.json()["type"].endswith("/codigo-invalido")
    assert flow.read(other["id"])["status"] == "APROBADO"
    assert flow.ledger(other["id"]) == []
    assert flow.cash_balance() == opening_balance


def test_pr11_wrong_code_does_not_reveal_an_expiry(flow, clock):
    """PR-11 / RN-03 / CA-06: only the right code can record the expired attempt."""
    disbursement = flow.approved()
    flow.issued_code(disbursement["id"])
    clock.advance(timedelta(hours=2))

    response = flow.confirm(disbursement["id"], WRONG_CODE)

    assert response.status_code == 422
    assert response.json()["type"].endswith("/codigo-invalido")
    assert flow.read(disbursement["id"])["status"] == "APROBADO"
    assert flow.ledger(disbursement["id"]) == []


@pytest.mark.parametrize("validator", [OTHER_COLLECTOR, ADMIN])
def test_pr11_only_the_collector_of_the_route_validates(flow, validator):
    """PR-11 / CA-05 / RN-03: the right code in the wrong hands changes nothing."""
    opening_balance = flow.cash_balance()
    disbursement = flow.approved()
    code = flow.issued_code(disbursement["id"])

    response = flow.confirm(disbursement["id"], code, actor=validator)

    assert response.status_code == 403
    assert response.json()["type"].endswith("/validador-no-autorizado")
    assert flow.read(disbursement["id"])["status"] == "APROBADO"
    assert flow.ledger(disbursement["id"]) == []
    assert flow.cash_balance() == opening_balance

    confirmed = flow.confirm(disbursement["id"], code, actor=COLLECTOR)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["confirmed_by"] == COLLECTOR


def test_pr11_repeating_after_the_expiry_returns_the_same_refusal(flow, clock):
    """PR-11 / CA-06 / RN-03 / INV-02: the repeat gets the same 409 and leaves no second entry."""
    opening_balance = flow.cash_balance()
    disbursement = flow.approved()
    code = flow.issued_code(disbursement["id"])
    clock.advance(timedelta(hours=2))
    first = flow.confirm(disbursement["id"], code)
    resolved_at = flow.read(disbursement["id"])["resolved_at"]
    clock.advance(timedelta(hours=1))

    repeat = flow.confirm(disbursement["id"], code)

    assert (first.status_code, repeat.status_code) == (409, 409)
    assert repeat.json() == first.json()
    assert repeat.json()["type"].endswith("/codigo-caducado")
    read = flow.read(disbursement["id"])
    assert read["status"] == "CADUCADO"
    assert read["resolved_at"] == resolved_at
    [entry] = flow.ledger(disbursement["id"])
    assert entry["entry_type"] == "DESEMBOLSO_CADUCADO"
    assert flow.cash_balance() == opening_balance
