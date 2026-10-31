"""PR-10, request limits over the API. UC-01, UC-02. RF-03, RN-06, flow steps 1 to 4."""

import pytest
from support import ADMIN, COLLECTOR, OTHER_ADMIN

from royexa.seed import COLLECTOR_LIMIT, ROUTE_LIMIT

OVER_COLLECTOR_LIMIT = COLLECTOR_LIMIT.cents + 1
OVER_ROUTE_LIMIT = ROUTE_LIMIT.cents + 1
OTHER_COLLECTOR = "cobrador-2"
OTHER_ROUTE_CLIENT = "cliente-4"
REASON = "cliente con buen historial"


@pytest.mark.parametrize("actor", [COLLECTOR, ADMIN])
def test_pr10_amount_over_the_route_limit_is_refused(flow, actor):
    """PR-10 / RF-03 / flow step 2: the route limit holds for whoever requests."""
    opening_balance = flow.cash_balance()

    response = flow.request(actor=actor, amount_cents=OVER_ROUTE_LIMIT)

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"].endswith("/monto-sobre-limite-de-ruta")
    assert flow.notices() == []
    assert flow.ledger() == []
    assert flow.cash_balance() == opening_balance


def test_pr10_amount_at_the_route_limit_is_accepted(flow):
    """PR-10 / RF-03 / flow steps 2 and 3: the limit itself fits, and it waits."""
    disbursement = flow.requested(amount_cents=ROUTE_LIMIT.cents)

    assert disbursement["status"] == "EN_ESPERA_AUTORIZACION"


def test_pr10_client_of_another_route_is_refused(flow):
    """PR-10 / RF-03 / flow step 1: a collector requests only for clients of their route."""
    response = flow.request(actor=COLLECTOR, client=OTHER_ROUTE_CLIENT)

    assert response.status_code == 403
    assert response.json()["type"].endswith("/cliente-fuera-de-ruta")
    assert flow.notices() == []
    assert flow.ledger() == []


def test_pr10_collector_of_the_route_may_request_for_that_client(flow):
    """PR-10 / flow step 1: the refusal is about the route, not about the client."""
    disbursement = flow.requested(actor=OTHER_COLLECTOR, client=OTHER_ROUTE_CLIENT)

    assert disbursement["status"] == "SOLICITADO"
    assert disbursement["collector_id"] == OTHER_COLLECTOR


def test_pr10_amount_at_the_collector_limit_advances(flow):
    """PR-10 / RF-03 / flow step 3: only an amount above the limit waits."""
    disbursement = flow.requested(amount_cents=COLLECTOR_LIMIT.cents)

    assert disbursement["status"] == "SOLICITADO"


def test_pr10_amount_over_the_collector_limit_waits_for_authorization(flow):
    """PR-10 / RF-03 / flow step 3: waiting issues no code and moves no money."""
    opening_balance = flow.cash_balance()

    disbursement = flow.requested(amount_cents=OVER_COLLECTOR_LIMIT)

    assert disbursement["status"] == "EN_ESPERA_AUTORIZACION"
    assert disbursement["code_expires_at"] is None
    assert flow.notices(disbursement["id"]) == []
    assert flow.cash_balance() == opening_balance


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_pr10_authorization_over_the_limit_needs_a_reason(flow, reason):
    """PR-10 / RF-03 / flow step 4: without a reason no code is issued and no money moves."""
    opening_balance = flow.cash_balance()
    disbursement = flow.requested(amount_cents=OVER_COLLECTOR_LIMIT)

    response = flow.approve(disbursement["id"], reason=reason)

    assert response.status_code == 422
    assert response.json()["type"].endswith("/motivo-requerido")
    read = flow.read(disbursement["id"])
    assert read["status"] == "EN_ESPERA_AUTORIZACION"
    assert read["approved_by"] is None
    assert read["code_expires_at"] is None
    assert flow.notices(disbursement["id"]) == []
    assert flow.ledger(disbursement["id"]) == []
    assert flow.cash_balance() == opening_balance


def test_pr10_authorized_request_settles_like_any_other(flow):
    """PR-10 / RF-03 / CA-05: with a reason it issues a code, and the code settles it."""
    opening_balance = flow.cash_balance()
    disbursement = flow.requested(amount_cents=OVER_COLLECTOR_LIMIT)

    approved = flow.approve(disbursement["id"], reason=REASON)

    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APROBADO"
    assert approved.json()["decision_reason"] == REASON
    code = flow.issued_code(disbursement["id"])
    assert flow.confirm(disbursement["id"], code).json()["status"] == "CONFIRMADO"
    assert flow.cash_balance() == opening_balance - OVER_COLLECTOR_LIMIT


def test_pr10_request_waiting_for_authorization_can_be_rejected(flow):
    """PR-10 / RF-03 / flow step 4: rejecting is open while the request waits."""
    disbursement = flow.requested(amount_cents=OVER_COLLECTOR_LIMIT)

    response = flow.reject(disbursement["id"], reason=REASON)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "RECHAZADO"


def test_pr10_self_approval_is_refused_even_with_a_reason(flow):
    """PR-10 / RN-06 / CA-06: a reason does not lift the rule, and another admin can decide."""
    disbursement = flow.requested(actor=ADMIN, amount_cents=OVER_COLLECTOR_LIMIT)

    response = flow.approve(disbursement["id"], actor=ADMIN, reason=REASON)

    assert response.status_code == 403
    assert response.json()["type"].endswith("/autoaprobacion-prohibida")
    assert flow.read(disbursement["id"])["status"] == "EN_ESPERA_AUTORIZACION"
    assert flow.approve(disbursement["id"], actor=OTHER_ADMIN, reason=REASON).status_code == 200
