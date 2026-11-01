"""PR-02, business rule over the API. UC-02. RN-06, CA-06, EC-02, EV-11, RF-03."""

from support import ADMIN, COLLECTOR, OTHER_ADMIN


def test_pr02_admin_cannot_approve_what_they_requested(flow):
    """PR-02 / RN-06 / EC-02 / EV-11: no administrator exception exists (DIV-07)."""
    disbursement = flow.requested(actor=ADMIN)

    response = flow.approve(disbursement["id"], actor=ADMIN)

    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"].endswith("/autoaprobacion-prohibida")
    read = flow.read(disbursement["id"])
    assert read["status"] == "SOLICITADO"
    assert read["approved_by"] is None
    assert [attempt["actor_id"] for attempt in read["rejected_approval_attempts"]] == [ADMIN]
    assert flow.notices(disbursement["id"]) == [], "EC-02: a rejected attempt never issues a code"


def test_pr02_collector_cannot_approve_their_own_request(flow):
    """PR-02 / EV-11: the collector who requested it is rejected and identified."""
    disbursement = flow.requested(actor=COLLECTOR)

    response = flow.approve(disbursement["id"], actor=COLLECTOR)

    assert response.status_code == 403
    read = flow.read(disbursement["id"])
    assert read["status"] == "SOLICITADO"
    assert [attempt["actor_id"] for attempt in read["rejected_approval_attempts"]] == [COLLECTOR]
    assert flow.notices(disbursement["id"]) == []


def test_pr02_a_different_admin_can_still_approve_after_the_rejection(flow):
    """PR-02 / CA-05 / CA-06: the request stays pending, not poisoned, after the attempt."""
    disbursement = flow.requested(actor=ADMIN)
    flow.approve(disbursement["id"], actor=ADMIN)

    response = flow.approve(disbursement["id"], actor=OTHER_ADMIN)

    assert response.status_code == 200, response.text
    assert response.json()["approved_by"] == OTHER_ADMIN
    assert [notice["kind"] for notice in flow.notices(disbursement["id"])] == ["CODIGO_CONFIRMACION"]
