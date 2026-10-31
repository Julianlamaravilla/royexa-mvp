"""PR-04, business rule. UC-01 and UC-04. CA-10, RN-05, RF-03."""

from support import ADMIN, COLLECTOR

UNPAID_CLIENT = "cliente-2"
SETTLED_CLIENT = "cliente-3"


def test_pr04_unpaid_prior_loan_blocks_the_request(flow):
    """PR-04 / CA-10 / RN-05: a balance on the prior loan rejects the operation."""
    response = flow.request(client=UNPAID_CLIENT)

    assert response.status_code == 409
    assert response.json()["type"].endswith("/prestamo-anterior-sin-liquidar")


def test_pr04_settled_prior_loan_does_not_block(flow):
    """PR-04 / RN-05: a loan paid in full lets a new disbursement through."""
    assert flow.request(client=SETTLED_CLIENT).status_code == 201


def test_pr04_registered_exception_unblocks_once(flow):
    """PR-04 / CA-10 / RN-05: only an explicit exception continues, and it is single use."""
    exception = flow.grant_exception(UNPAID_CLIENT, reason="cliente recurrente").json()

    disbursement = flow.requested(client=UNPAID_CLIENT)

    assert disbursement["renewal_exception_id"] == exception["id"]
    assert exception["granted_by"] == ADMIN
    assert exception["prior_loan_id"] == "prestamo-impago"
    assert flow.request(client=UNPAID_CLIENT).status_code == 409


def test_pr04_only_an_administrator_grants_the_exception(flow):
    """PR-04 / RN-05: the exception is the administrator's to give."""
    assert flow.grant_exception(UNPAID_CLIENT, actor=COLLECTOR).status_code == 403


def test_pr04_exception_needs_an_unpaid_loan_and_a_reason(flow):
    """PR-04 / RN-05: nothing to except, or no reason, grants nothing."""
    assert flow.grant_exception(SETTLED_CLIENT).status_code == 403
    assert flow.grant_exception(UNPAID_CLIENT, reason=" ").status_code == 422


def test_pr04_rule_holds_again_when_the_money_moves(flow):
    """PR-04 / RN-05: two open requests cannot both become loans for one client."""
    first = flow.approved()
    second = flow.approved()
    first_code = flow.issued_code(first["id"])
    second_code = flow.issued_code(second["id"])
    balance = flow.cash_balance()

    assert flow.confirm(first["id"], first_code).status_code == 200
    response = flow.confirm(second["id"], second_code)

    assert response.status_code == 409
    assert response.json()["type"].endswith("/prestamo-anterior-sin-liquidar")
    assert flow.cash_balance() == balance - first["amount_cents"]
    assert flow.ledger(second["id"]) == []
