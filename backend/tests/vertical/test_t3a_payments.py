"""T3a, RF-01: a collector registers a payment; CA-01, RN-01. Runs on both adapters."""

from support import ADMIN, COLLECTOR


def _ledger_payments(flow) -> list[dict]:
    return [entry for entry in flow.ledger() if entry["entry_type"] == "PAGO"]


def test_ca01_a_partial_payment_advances_the_counter_fractionally(flow):
    """CA-01 over the loan the flow produces: 20 installments of 60, a payment of 30."""
    loan = flow.confirmed()["loan"]
    assert (loan["installment_count"], loan["remaining_installments"]) == (20, "20")

    response = flow.pay(loan["id"], 3_000)

    assert response.status_code == 201, response.text
    result = response.json()
    assert result["loan"]["remaining_installments"] == "19.5"
    assert result["loan"]["outstanding_cents"] == 117_000
    assert result["loan"]["installment_count"] == 20
    payment = result["payment"]
    assert payment["method"] == "EFECTIVO"
    assert payment["collector_id"] == COLLECTOR
    assert payment["allocations"] == [{"sequence": 1, "amount_cents": 3_000}]
    read = flow._get(f"/v1/loans/{loan['id']}").json()
    assert read["remaining_installments"] == "19.5"
    assert read["installments"][0]["paid_cents"] == 3_000


def test_ca01_the_payment_is_readable_with_the_identity_of_the_collector(flow):
    loan = flow.confirmed()["loan"]
    registered = flow.pay(loan["id"], 3_000, "TRANSFERENCIA").json()["payment"]

    listed = flow._get(f"/v1/loans/{loan['id']}/payments", ADMIN).json()

    assert listed == [registered]
    assert (listed[0]["collector_id"], listed[0]["method"]) == (COLLECTOR, "TRANSFERENCIA")


def test_t3a_a_cash_payment_adds_to_the_box_and_leaves_its_ledger_entry(flow):
    loan = flow.confirmed()["loan"]
    before = flow.cash_balance()

    payment = flow.pay(loan["id"], 3_000).json()["payment"]

    assert flow.cash_balance() == before + 3_000
    entries = _ledger_payments(flow)
    assert len(entries) == 1
    assert (entries[0]["amount_cents"], entries[0]["cash_effect_cents"]) == (3_000, 3_000)
    assert entries[0]["payment_id"] == payment["id"]
    assert entries[0]["disbursement_id"] is None
    assert entries[0]["actor_id"] == COLLECTOR


def test_t3a_a_transfer_is_recorded_but_adds_no_cash(flow):
    loan = flow.confirmed()["loan"]
    before = flow.cash_balance()

    response = flow.pay(loan["id"], 3_000, "TRANSFERENCIA")

    assert response.status_code == 201
    assert flow.cash_balance() == before
    entry = _ledger_payments(flow)[0]
    assert (entry["amount_cents"], entry["cash_effect_cents"]) == (3_000, 0)
    assert entry["payment_method"] == "TRANSFERENCIA"
    assert flow._get(f"/v1/loans/{loan['id']}").json()["outstanding_cents"] == 117_000


def test_rn01_an_excess_over_one_installment_goes_to_the_next(flow):
    loan = flow.confirmed()["loan"]

    result = flow.pay(loan["id"], 7_000).json()

    assert result["payment"]["allocations"] == [
        {"sequence": 1, "amount_cents": 6_000},
        {"sequence": 2, "amount_cents": 1_000},
    ]
    # 18 whole installments and 5/6 of another: no finite decimal, so the exact fraction.
    assert result["loan"]["remaining_installments"] == "113/6"


def test_rn01_a_payment_over_the_balance_is_refused_and_leaves_no_trace(flow):
    loan = flow.confirmed()["loan"]
    before = flow.cash_balance()

    response = flow.pay(loan["id"], 120_001)

    assert response.status_code == 422
    assert response.json()["type"].endswith("/pago-excede-saldo")
    assert flow.cash_balance() == before
    assert _ledger_payments(flow) == []
    assert flow._get(f"/v1/loans/{loan['id']}/payments").json() == []
    assert flow._get(f"/v1/loans/{loan['id']}").json()["outstanding_cents"] == 120_000


def test_t3a_paying_the_whole_balance_settles_the_loan_and_allows_a_renewal(flow):
    """RN-05 reads the balance the payments leave: a settled client may renew."""
    assert flow.request(client="cliente-2").status_code == 409

    response = flow.pay("prestamo-impago", 70_000)

    assert response.status_code == 201
    assert response.json()["loan"]["status"] == "LIQUIDADO"
    assert flow.request(client="cliente-2").status_code == 201


def test_t3a_only_the_collector_of_the_route_registers_a_payment(flow):
    loan = flow.confirmed()["loan"]

    assert flow.pay(loan["id"], 3_000, actor=ADMIN).status_code == 403
    assert flow.pay(loan["id"], 3_000, actor="cobrador-2").status_code == 403
    assert flow.pay(loan["id"], 3_000, actor="nadie").status_code == 401
    assert flow._get(f"/v1/loans/{loan['id']}/payments").json() == []


def test_t3a_an_invalid_request_is_rejected_before_any_effect(flow):
    loan = flow.confirmed()["loan"]

    assert flow.pay(loan["id"], 0).status_code == 422
    assert flow.pay(loan["id"], -5).status_code == 422
    assert flow.pay(loan["id"], 3_000, method="CHEQUE").status_code == 422
    assert flow.pay("no-existe", 3_000).status_code == 404
    assert flow._get("/v1/loans/no-existe/payments").status_code == 404
