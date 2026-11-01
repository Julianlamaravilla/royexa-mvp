"""PR-09, alternative outcome of UC-02 over the API. RF-03, RN-03, flow step 4."""

import pytest
from support import ADMIN, COLLECTOR

REASON = "historial de pagos insuficiente"


def test_pr09_rejection_records_the_decision_and_releases_nothing(flow):
    """PR-09 / RF-03 / RN-03: a rejected request has no code and moves no money."""
    opening_balance = flow.cash_balance()
    disbursement = flow.requested()

    response = flow.reject(disbursement["id"], reason=REASON)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "RECHAZADO"
    assert body["decided_by"] == ADMIN
    assert body["decision_reason"] == REASON
    assert body["approved_by"] is None
    assert body["code_expires_at"] is None
    assert body["loan"] is None
    assert flow.notices(disbursement["id"]) == [], "flow step 5: only an approval issues a code"
    assert flow.ledger(disbursement["id"]) == []
    assert flow.cash_balance() == opening_balance


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_pr09_rejection_needs_a_reason(flow, reason):
    """PR-09 / RF-03 / flow step 4: without a reason the request stays undecided."""
    disbursement = flow.requested()

    response = flow.reject(disbursement["id"], reason=reason)

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"].endswith("/motivo-requerido")
    read = flow.read(disbursement["id"])
    assert read["status"] == "SOLICITADO"
    assert read["decided_by"] is None
    assert flow.reject(disbursement["id"], reason=REASON).status_code == 200


def test_pr09_only_an_administrator_rejects(flow):
    """PR-09 / RF-03: a collector is refused at the entry and the request is untouched."""
    disbursement = flow.requested()

    response = flow.reject(disbursement["id"], actor=COLLECTOR, reason=REASON)

    assert response.status_code == 403
    assert response.json()["type"].endswith("/rol-administrador-requerido")
    read = flow.read(disbursement["id"])
    assert read["status"] == "SOLICITADO"
    assert read["decided_by"] is None


def test_pr09_confirmation_after_a_rejection_is_refused(flow):
    """PR-09 / RN-03: nothing can be confirmed on a rejected request."""
    opening_balance = flow.cash_balance()
    disbursement = flow.requested()
    flow.reject(disbursement["id"], reason=REASON)

    response = flow.confirm(disbursement["id"], "ABCD1234")

    assert response.status_code == 409
    assert response.json()["type"].endswith("/transicion-invalida")
    assert flow.read(disbursement["id"])["status"] == "RECHAZADO"
    assert flow.ledger(disbursement["id"]) == []
    assert flow.cash_balance() == opening_balance


def test_pr09_a_rejection_cannot_be_approved_later(flow):
    """PR-09 / RF-03 / RN-03: a late approval issues no code."""
    disbursement = flow.requested()
    flow.reject(disbursement["id"], reason=REASON)

    response = flow.approve(disbursement["id"])

    assert response.status_code == 409
    assert response.json()["type"].endswith("/transicion-invalida")
    assert flow.read(disbursement["id"])["status"] == "RECHAZADO"
    assert flow.notices(disbursement["id"]) == []


def test_pr09_an_approved_request_cannot_be_rejected(flow):
    """PR-09 / RF-03: the decision is taken once; the issued code stays valid."""
    disbursement = flow.approved()

    response = flow.reject(disbursement["id"], reason=REASON)

    assert response.status_code == 409
    assert response.json()["type"].endswith("/transicion-invalida")
    read = flow.read(disbursement["id"])
    assert read["status"] == "APROBADO"
    assert read["decision_reason"] is None
