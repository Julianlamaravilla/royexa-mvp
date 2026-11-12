"""PR-01, main scenario. UC-03 over the API. CA-05, CA-07, RN-03, RN-04, RF-03, RF-04."""

from datetime import date

from support import ADMIN, COLLECTOR, DEVICE_TIME


def test_pr01_valid_code_records_entry_schedule_and_cash_deduction(flow, clock):
    """PR-01 / CA-05 / RN-03 / RN-04: a valid code settles every effect at once."""
    opening_balance = flow.cash_balance()
    disbursement = flow.requested(amount_cents=100_000, term_days=20, installment_count=20)
    assert disbursement["status"] == "SOLICITADO"

    approved = flow.approve(disbursement["id"]).json()
    assert approved["status"] == "APROBADO"
    assert flow.cash_balance() == opening_balance, "RN-03: approval releases no money"
    assert flow.ledger(disbursement["id"]) == [], "RN-03: approval writes no entry"

    code = flow.issued_code(disbursement["id"])
    response = flow.confirm(disbursement["id"], code)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "CONFIRMADO"
    assert body["requested_by"] == COLLECTOR
    assert body["approved_by"] == ADMIN
    assert flow.cash_balance() == opening_balance - 100_000

    # CA-09: 1000 at 20 installments with a fixed interest of 200 gives 20 installments of 60.
    schedule = body["loan"]["installments"]
    assert [item["amount_cents"] for item in schedule] == [6_000] * 20
    assert all(date.fromisoformat(item["due_date"]).isoweekday() != 7 for item in schedule)

    [entry] = flow.ledger(disbursement["id"])
    assert entry["entry_type"] == "DESEMBOLSO"
    assert entry["amount_cents"] == 100_000
    assert entry["actor_id"] == COLLECTOR
    assert entry["device_time"] == DEVICE_TIME.replace("+00:00", "Z")
    assert entry["server_time"] == clock.now().isoformat().replace("+00:00", "Z")
    assert entry["cash_box_id"] == "caja-cobrador-1-2026-10-30"


def test_pr01_result_is_queryable_with_who_requested_and_who_approved(flow):
    """PR-01 / CA-05: the operation stays readable with both identities."""
    disbursement = flow.approved()
    flow.confirm(disbursement["id"], flow.issued_code(disbursement["id"]))

    read = flow.read(disbursement["id"])

    assert read["status"] == "CONFIRMADO"
    assert (read["requested_by"], read["approved_by"]) == (COLLECTOR, ADMIN)
    assert len(read["ledger_entries"]) == 1


def test_pr01_response_never_reveals_the_code_to_the_collector(flow):
    """PR-01 / RN-03: the code reaches the client through the notifier only."""
    disbursement = flow.approved()
    code = flow.issued_code(disbursement["id"])

    assert code not in flow.approve(disbursement["id"]).text
    assert code not in str(flow.read(disbursement["id"]))
    assert code not in str(flow.notices(disbursement["id"]))
