"""T3b, RF-01: a non-payment with its reason and commitment, and the clients pending a visit.

CA-02, T3-P1 and T3-P2. Runs on both adapters. FakeClock starts on Friday 2026-10-30.
"""

from datetime import timedelta

from support import ADMIN, COLLECTOR


def _new_client_with_loan(flow) -> tuple[str, dict]:
    client = flow._post("/v1/clients", ADMIN, {"name": "Cliente de ruta", "route_id": "ruta-1"})
    assert client.status_code == 201
    client_id = client.json()["id"]
    return client_id, flow.confirmed(client=client_id)["loan"]


def test_ca02_a_non_payment_keeps_its_reason_and_commitment_and_leaves_the_balance(flow):
    client, loan = _new_client_with_loan(flow)
    box = flow.cash_balance()
    assert client in flow.pending_clients()

    response = flow.non_pay(loan["id"], "no tiene dinero", "2026-11-02")

    assert response.status_code == 201, response.text
    registered = response.json()
    assert (registered["reason"], registered["commitment_date"]) == ("no tiene dinero", "2026-11-02")
    assert (registered["collector_id"], registered["client_id"]) == (COLLECTOR, client)
    assert client not in flow.pending_clients()
    assert flow._get(f"/v1/loans/{loan['id']}/non-payments", ADMIN).json() == [registered]
    after = flow._get(f"/v1/loans/{loan['id']}").json()
    assert after["outstanding_cents"] == loan["outstanding_cents"]
    assert flow._get(f"/v1/loans/{loan['id']}/payments").json() == []
    assert flow.cash_balance() == box
    assert [e for e in flow.ledger() if e["entry_type"] == "PAGO"] == []


def test_t3p1_only_clients_with_an_active_loan_on_the_route_are_pending(flow):
    # cliente-1 has no loan, cliente-3 settled his, cliente-4 belongs to another route.
    assert flow.pending_clients() == ["cliente-2"]
    assert flow.pending_clients("ruta-2", actor=ADMIN) == []


def test_t3p1_a_pending_row_says_what_the_collector_needs_for_the_visit(flow):
    row = flow.pending().json()[0]

    assert row == {
        "client_id": "cliente-2",
        "client_name": "Cliente con saldo pendiente",
        "loan_id": "prestamo-impago",
        "outstanding_cents": 70_000,
        "remaining_installments": "7/12",
    }


def test_t3p1_a_payment_also_ends_the_pending_visit_but_a_settled_client_never_was(flow):
    assert flow.pay("prestamo-impago", 1_000).status_code == 201

    assert flow.pending_clients() == []


def test_t3p1_the_visit_counts_for_its_day_only(flow, clock):
    assert flow.non_pay("prestamo-impago", commitment_date="2026-11-02").status_code == 201
    assert flow.pending_clients() == []

    clock.advance(timedelta(days=1))  # Saturday 31 October, a collection day

    assert flow.pending_clients() == ["cliente-2"]


def test_t3p1_sunday_is_not_a_collection_day(flow):
    assert flow.pending_clients(day="2026-11-01") == []
    assert flow.pending_clients(day="2026-11-02") == ["cliente-2"]


def test_t3p1_the_collector_of_the_route_and_the_administrator_read_it(flow):
    assert flow.pending(actor=ADMIN).status_code == 200
    assert flow.pending(actor="cobrador-2").status_code == 403
    assert flow.pending("ruta-9").status_code == 404
    assert flow.pending(actor="nadie").status_code == 401


def test_t3p2_the_commitment_must_fall_after_the_day_of_the_registration(flow):
    for day in ("2026-10-29", "2026-10-30"):
        refused = flow.non_pay("prestamo-impago", commitment_date=day)
        assert refused.status_code == 422, day
        assert refused.json()["type"].endswith("/compromiso-invalido")

    assert flow.non_pay("prestamo-impago", commitment_date=None).status_code == 422
    assert flow.non_pay("prestamo-impago", commitment_date="2026-10-31").status_code == 201


def test_t3p2_the_commitment_makes_nobody_pending_and_changes_no_balance(flow):
    flow.non_pay("prestamo-impago", commitment_date="2026-10-31")

    assert flow.pending_clients() == []
    assert flow._get("/v1/loans/prestamo-impago").json()["outstanding_cents"] == 70_000


def test_t3b_a_non_payment_needs_a_reason(flow):
    for reason in ("", "   "):
        response = flow.non_pay("prestamo-impago", reason=reason)
        assert response.status_code == 422, reason

    assert flow._get("/v1/loans/prestamo-impago/non-payments").json() == []
    assert flow.pending_clients() == ["cliente-2"]


def test_t3b_only_the_collector_of_the_route_registers_a_non_payment(flow):
    assert flow.non_pay("prestamo-impago", actor=ADMIN).status_code == 403
    assert flow.non_pay("prestamo-impago", actor="cobrador-2").status_code == 403
    assert flow._get("/v1/loans/prestamo-impago/non-payments").json() == []


def test_t3b_a_settled_or_unknown_loan_takes_no_non_payment(flow):
    settled = flow.non_pay("prestamo-liquidado")
    assert settled.status_code == 409
    assert settled.json()["type"].endswith("/prestamo-liquidado")
    assert flow.non_pay("no-existe").status_code == 404
    assert flow._get("/v1/loans/no-existe/non-payments").status_code == 404
