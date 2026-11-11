"""T2b, RF-05: loans and their installment schedule are readable; CA-09 and CA-10.

Every client below is registered through the API. Runs on both adapters.
"""

from support import ADMIN, COLLECTOR


def _new_client(flow) -> str:
    response = flow._post("/v1/clients", ADMIN, {"name": "Cliente de la prueba", "route_id": "ruta-1"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _confirmed_loan(flow, client: str, **terms) -> dict:
    disbursement = flow.approved(client=client, **terms)
    code = flow.issued_code(disbursement["id"])
    response = flow.confirm(disbursement["id"], code)
    assert response.status_code == 200, response.text
    return response.json()["loan"]


def test_ca09_the_schedule_is_derived_from_amount_term_and_interest(flow):
    """CA-09: 1000 over 20 installments with a fixed interest of 200 gives 20 of 60, on
    collection days Monday to Saturday, readable afterwards."""
    client = _new_client(flow)
    loan = _confirmed_loan(flow, client, amount_cents=100_000, term_days=20, installment_count=20)

    read = flow._get(f"/v1/loans/{loan['id']}", COLLECTOR)

    assert read.status_code == 200
    stored = read.json()
    assert stored["client_id"] == client
    assert stored["status"] == "ACTIVO"
    assert (stored["principal_cents"], stored["interest_cents"]) == (100_000, 20_000)
    assert stored["outstanding_cents"] == 120_000
    installments = stored["installments"]
    assert len(installments) == 20
    assert {item["amount_cents"] for item in installments} == {6_000}
    due = [item["due_date"] for item in installments]
    assert due == sorted(set(due))
    assert due[:3] == ["2026-10-31", "2026-11-02", "2026-11-03"]  # Sunday 1 November skipped
    from datetime import date

    assert all(date.fromisoformat(day).isoweekday() != 7 for day in due)


def test_ca10_a_client_with_a_balance_cannot_renew_without_an_explicit_exception(flow):
    """CA-10: rejected and informed; it continues only after the administrator's exception."""
    client = _new_client(flow)
    first = _confirmed_loan(flow, client)

    refused = flow.request(client=client)

    assert refused.status_code == 409
    assert refused.json()["type"].endswith("/prestamo-anterior-sin-liquidar")
    assert refused.json()["detail"] == first["id"]
    assert flow.grant_exception(client, actor=COLLECTOR).status_code == 403
    assert flow.request(client=client).status_code == 409
    assert flow.grant_exception(client).status_code == 201
    assert flow.request(client=client).status_code == 201


def test_t2b_the_loans_of_a_client_come_in_the_order_they_were_granted(flow):
    settled = flow._get("/v1/clients/cliente-3/loans", COLLECTOR).json()
    renewed = _confirmed_loan(flow, "cliente-3")

    loans = flow._get("/v1/clients/cliente-3/loans", COLLECTOR).json()

    assert [loan["id"] for loan in settled] == ["prestamo-liquidado"]
    assert [loan["id"] for loan in loans] == ["prestamo-liquidado", renewed["id"]]
    assert [loan["status"] for loan in loans] == ["LIQUIDADO", "ACTIVO"]


def test_t2b_a_loan_with_a_balance_and_a_settled_one_report_their_state(flow):
    unpaid = flow._get("/v1/loans/prestamo-impago").json()
    settled = flow._get("/v1/loans/prestamo-liquidado").json()

    assert (unpaid["status"], unpaid["outstanding_cents"]) == ("ACTIVO", 70_000)
    assert (settled["status"], settled["outstanding_cents"]) == ("LIQUIDADO", 0)


def test_t2b_an_unknown_loan_or_client_is_not_found(flow):
    loan = flow._get("/v1/loans/no-existe")
    client = flow._get("/v1/clients/no-existe/loans")

    assert loan.status_code == 404
    assert loan.json()["type"].endswith("/prestamo-no-encontrado")
    assert client.status_code == 404
    assert client.json()["type"].endswith("/cliente-no-encontrado")


def test_t2b_a_client_without_loans_has_an_empty_list(flow):
    assert flow._get("/v1/clients/cliente-1/loans").json() == []
