"""T5c, RF-02: the three panels of the day (pending, paid, did not pay), with cash and
transfers told apart. T3-P1 defines who is pending. Runs on both adapters.

FakeClock starts on Friday 2026-10-30. The route holds the seeded cliente-1 (no loan),
cliente-2 (a loan with a balance) and cliente-3 (a settled loan), plus the clients each
test registers.
"""

from datetime import timedelta

from support import ADMIN, COLLECTOR


def _client_with_loan_from_yesterday(flow, clock, name: str) -> tuple[str, dict]:
    clock.advance(-timedelta(days=1))
    client = flow._post("/v1/clients", ADMIN, {"name": name, "route_id": "ruta-1"}).json()["id"]
    loan = flow.confirmed(client=client)["loan"]
    clock.advance(timedelta(days=1))
    return client, loan


def _ids(panel: list[dict]) -> list[str]:
    return [row["client_id"] for row in panel]


def test_t5c_before_any_visit_everyone_with_an_active_loan_is_pending(flow):
    body = flow.panels().json()

    assert body["day"] == "2026-10-30"
    assert (body["collector_id"], body["route_id"]) == (COLLECTOR, "ruta-1")
    assert _ids(body["pending"]) == ["cliente-2"]
    assert body["paid"] == [] and body["unpaid"] == []
    assert body["totals"] == {"cash_cents": 0, "transfer_cents": 0}


def test_t5c_the_pending_panel_is_the_list_of_pending_visits(flow):
    assert flow.panels().json()["pending"] == flow.pending().json()


def test_t5c_the_paid_panel_tells_cash_from_transfer(flow, clock):
    client, loan = _client_with_loan_from_yesterday(flow, clock, "Cliente que paga")
    flow.pay(loan["id"], 30_000, "EFECTIVO")
    flow.pay(loan["id"], 20_000, "TRANSFERENCIA")

    body = flow.panels().json()

    assert body["paid"] == [
        {
            "client_id": client,
            "client_name": "Cliente que paga",
            "cash_cents": 30_000,
            "transfer_cents": 20_000,
            "payments": 2,
        }
    ]
    assert body["totals"] == {"cash_cents": 30_000, "transfer_cents": 20_000}
    assert client not in _ids(body["pending"])


def test_t5c_a_transfer_only_payment_counts_no_cash(flow, clock):
    _, loan = _client_with_loan_from_yesterday(flow, clock, "Cliente por transferencia")
    flow.pay(loan["id"], 25_000, "TRANSFERENCIA")

    body = flow.panels().json()

    assert body["paid"][0]["cash_cents"] == 0
    assert body["totals"] == {"cash_cents": 0, "transfer_cents": 25_000}


def test_t5c_the_unpaid_panel_keeps_the_reason_and_the_commitment(flow, clock):
    client, loan = _client_with_loan_from_yesterday(flow, clock, "Cliente que no paga")
    flow.non_pay(loan["id"], "no tiene dinero", "2026-11-02")

    body = flow.panels().json()

    assert body["unpaid"] == [
        {
            "client_id": client,
            "client_name": "Cliente que no paga",
            "loan_id": loan["id"],
            "reason": "no tiene dinero",
            "commitment_date": "2026-11-02",
        }
    ]
    assert client not in _ids(body["pending"])
    assert body["paid"] == []


def test_t5c_a_client_who_paid_is_not_also_in_the_unpaid_panel(flow, clock):
    client, loan = _client_with_loan_from_yesterday(flow, clock, "Cliente mixto")
    flow.pay(loan["id"], 10_000)
    flow.non_pay(loan["id"], "solo pudo pagar una parte", "2026-11-02")

    body = flow.panels().json()

    assert _ids(body["paid"]) == [client]
    assert body["unpaid"] == []


def test_t5c_a_client_who_settles_the_loan_today_is_still_in_the_paid_panel(flow):
    flow.pay("prestamo-impago", 70_000)

    body = flow.panels().json()

    assert _ids(body["paid"]) == ["cliente-2"]
    assert body["pending"] == []


def test_t5c_the_three_panels_cover_every_client_with_an_active_loan_exactly_once(flow, clock):
    paying, paying_loan = _client_with_loan_from_yesterday(flow, clock, "Paga")
    missing, missing_loan = _client_with_loan_from_yesterday(flow, clock, "No paga")
    waiting, _ = _client_with_loan_from_yesterday(flow, clock, "Pendiente")
    route_clients = [c["id"] for c in flow._get("/v1/clients").json() if c["route_id"] == "ruta-1"]
    active = [
        client
        for client in route_clients
        if any(
            loan["status"] == "ACTIVO"
            for loan in flow._get(f"/v1/clients/{client}/loans").json()
        )
    ]
    flow.pay(paying_loan["id"], 5_000)
    flow.non_pay(missing_loan["id"])

    body = flow.panels().json()
    listed = _ids(body["pending"]) + _ids(body["paid"]) + _ids(body["unpaid"])

    assert sorted(listed) == sorted(set(listed)), "no client in two panels"
    assert set(active) <= set(listed)
    assert (paying in _ids(body["paid"]), missing in _ids(body["unpaid"])) == (True, True)
    assert {waiting, "cliente-2"} <= set(_ids(body["pending"]))
    assert not {"cliente-1", "cliente-3"} & set(listed), "no active loan, no visit"


def test_t5c_yesterdays_visits_do_not_count_today(flow, clock):
    client, loan = _client_with_loan_from_yesterday(flow, clock, "Cliente de ayer")
    flow.pay(loan["id"], 5_000)
    clock.advance(timedelta(days=1))  # Saturday

    body = flow.panels().json()

    assert body["day"] == "2026-10-31"
    assert body["paid"] == [] and body["unpaid"] == []
    assert client in _ids(body["pending"])
    assert body["totals"] == {"cash_cents": 0, "transfer_cents": 0}


def test_t5c_sunday_has_no_panels(flow, clock):
    clock.advance(timedelta(days=2))  # Sunday 1 November

    response = flow.panels()

    assert response.status_code == 200
    body = response.json()
    assert (body["pending"], body["paid"], body["unpaid"]) == ([], [], [])


def test_t5c_a_closed_day_can_still_be_read(flow, clock):
    _, loan = _client_with_loan_from_yesterday(flow, clock, "Cliente del cierre")
    flow.pay(loan["id"], 75_000)
    flow.visit_everyone()
    assert flow.close_box(75_000).status_code == 201

    body = flow.panels().json()

    assert body["totals"] == {"cash_cents": 75_000, "transfer_cents": 0}
    assert body["pending"] == []


def test_t5c_the_collector_of_the_box_and_an_administrator_read_it(flow):
    assert flow.panels(actor=ADMIN).status_code == 200
    assert flow.panels(actor="cobrador-2").status_code == 403
    assert flow.panels(actor="nadie").status_code == 401
    unknown = flow.panels(collector="nadie", actor=ADMIN)
    assert unknown.status_code == 404


def test_t5c_a_client_who_settled_and_renewed_today_is_paid_and_not_pending(flow):
    """T3-P1 speaks of the client: a payment on any of his loans ends his pending visit."""
    flow.pay("prestamo-impago", 70_000)
    renewed = flow.confirmed(client="cliente-2")["loan"]

    body = flow.panels().json()

    assert _ids(body["paid"]) == ["cliente-2"]
    assert "cliente-2" not in _ids(body["pending"])
    assert flow._get(f"/v1/loans/{renewed['id']}").json()["status"] == "ACTIVO"
    assert flow.pending_clients() == []
