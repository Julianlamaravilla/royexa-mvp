"""PR-03, alternative scenario. UC-03. CA-06, RN-03, RN-04, RF-03."""

from datetime import timedelta


def test_pr03_expired_code_rejects_without_deduction_and_leaves_reason_entry(flow, clock):
    """PR-03 / CA-06 / RN-03: expiry moves no money and records why."""
    opening_balance = flow.cash_balance()
    disbursement = flow.approved()
    code = flow.issued_code(disbursement["id"])
    clock.advance(timedelta(hours=2))

    response = flow.confirm(disbursement["id"], code)

    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"].endswith("/codigo-caducado")
    assert flow.cash_balance() == opening_balance
    read = flow.read(disbursement["id"])
    assert read["status"] == "CADUCADO"
    assert read["loan"] is None
    [entry] = flow.ledger(disbursement["id"])
    assert entry["entry_type"] == "DESEMBOLSO_CADUCADO"
    assert entry["reason"] == "codigo_caducado"
    assert entry["actor_id"] == "cobrador-1"
