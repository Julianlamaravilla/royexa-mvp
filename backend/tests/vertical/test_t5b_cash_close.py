"""T5b, RF-02: closing the day's cash box; CA-03, CA-04, RN-02 and T5-P1.

Amounts in cents: CA-03's 750 / 725 / 25 are 75,000 / 72,500 / 2,500. FakeClock starts on
Friday 2026-10-30. Runs on both adapters (fixture `backend`).
"""

from datetime import timedelta

from support import ADMIN, COLLECTOR


def _loan_from_yesterday(flow, clock) -> dict:
    """A client with an active loan granted on Thursday, so Friday's box starts clean."""
    clock.advance(-timedelta(days=1))
    client = flow._post("/v1/clients", ADMIN, {"name": "Cliente del cierre", "route_id": "ruta-1"})
    loan = flow.confirmed(client=client.json()["id"])["loan"]
    clock.advance(timedelta(days=1))
    return loan


def _ready_to_close(flow, clock, cash: int = 75_000) -> dict:
    """Friday: `cash` collected in cash and every client visited."""
    loan = _loan_from_yesterday(flow, clock)
    if cash:
        assert flow.pay(loan["id"], cash).status_code == 201
    flow.visit_everyone()
    return loan


def _box(flow) -> dict:
    return flow._get(f"/v1/cash-boxes/{COLLECTOR}", COLLECTOR).json()


def test_ca03_the_close_shows_the_difference_between_registered_and_delivered(flow, clock):
    _ready_to_close(flow, clock, cash=75_000)

    response = flow.close_box(72_500)

    assert response.status_code == 201, response.text
    closed = response.json()
    assert (closed["expected_cents"], closed["delivered_cents"]) == (75_000, 72_500)
    assert closed["discrepancy_cents"] == -2_500
    assert (closed["collector_id"], closed["closed_by"], closed["day"]) == (
        COLLECTOR,
        COLLECTOR,
        "2026-10-30",
    )
    assert _box(flow)["closed"] is True


def test_ca03_the_discrepancy_is_on_record_for_the_administrator(flow, clock):
    _ready_to_close(flow, clock)
    closed = flow.close_box(72_500).json()

    listed = flow.cash_closes().json()

    assert listed == [closed]
    assert flow.cash_closes(f"?collector_id={COLLECTOR}&date=2026-10-30").json() == [closed]
    assert flow.cash_closes("?date=2026-10-29").json() == []
    assert flow.cash_closes("?collector_id=cobrador-2").json() == []
    assert flow.cash_closes(actor=COLLECTOR).status_code == 403


def test_t5p1_transfers_do_not_enter_the_expected_cash(flow, clock):
    loan = _loan_from_yesterday(flow, clock)
    flow.pay(loan["id"], 30_000, "EFECTIVO")
    flow.pay(loan["id"], 20_000, "TRANSFERENCIA")
    flow.visit_everyone()

    closed = flow.close_box(30_000).json()

    assert (closed["expected_cents"], closed["discrepancy_cents"]) == (30_000, 0)


def test_t5p1_confirmed_disbursements_of_the_day_lower_the_expected_cash(flow, clock):
    loan = _loan_from_yesterday(flow, clock)
    flow.pay(loan["id"], 30_000)
    flow.confirmed(client="cliente-1")  # 100,000 handed out today
    flow.visit_everyone()

    closed = flow.close_box(0).json()

    assert closed["expected_cents"] == 30_000 - 100_000
    assert closed["discrepancy_cents"] == 70_000, "delivered minus expected, with its sign"


def test_t5p1_what_is_delivered_is_never_negative(flow, clock):
    _ready_to_close(flow, clock)

    assert flow.close_box(-1).status_code == 422
    assert _box(flow)["closed"] is False


def test_rf07_a_zero_difference_is_recorded_as_zero(flow, clock):
    _ready_to_close(flow, clock, cash=75_000)

    closed = flow.close_box(75_000).json()

    assert closed["discrepancy_cents"] == 0
    assert flow.cash_closes().json()[0]["discrepancy_cents"] == 0


def test_t5b_a_day_without_cash_movements_closes_with_nothing_expected(flow, clock):
    flow.visit_everyone()

    closed = flow.close_box(0).json()

    assert (closed["expected_cents"], closed["discrepancy_cents"]) == (0, 0)


def test_ca04_pending_visits_reject_the_close_and_the_box_stays_open(flow):
    response = flow.close_box(0)

    assert response.status_code == 409
    assert response.json()["type"].endswith("/visitas-pendientes")
    assert "cliente-2" in response.json()["detail"]
    assert _box(flow)["closed"] is False
    assert flow.cash_closes().json() == []
    assert flow.pay("prestamo-impago", 1_000).status_code == 201, "the box still takes money"


def test_rn02_a_closed_box_takes_no_further_movement(flow, clock):
    loan = _ready_to_close(flow, clock)
    pending = flow.approved(client="cliente-3")
    code = flow.issued_code(pending["id"])
    flow.close_box(75_000)

    payment = flow.pay(loan["id"], 1_000)
    confirmation = flow.confirm(pending["id"], code)

    for refused in (payment, confirmation):
        assert refused.status_code == 409
        assert refused.json()["type"].endswith("/caja-cerrada")
    assert flow.read(pending["id"])["status"] == "APROBADO"
    assert len(flow._get(f"/v1/loans/{loan['id']}/payments").json()) == 1
    assert _box(flow)["balance_cents"] == 100_000_000 + 75_000


def test_rn02_the_close_is_irreversible(flow, clock):
    _ready_to_close(flow, clock)
    assert flow.close_box(75_000).status_code == 201

    again = flow.close_box(75_000)

    assert again.status_code == 409
    assert again.json()["type"].endswith("/caja-cerrada")
    assert len(flow.cash_closes().json()) == 1


def test_rn02_the_next_day_opens_a_fresh_box_while_the_closed_one_stays_closed(flow, clock):
    loan = _ready_to_close(flow, clock)
    flow.close_box(75_000)
    clock.advance(timedelta(days=1))  # Saturday

    assert flow.pay(loan["id"], 1_000).status_code == 201

    today = _box(flow)
    friday = flow._get(f"/v1/cash-boxes/{COLLECTOR}?date=2026-10-30").json()
    assert (today["day"], today["closed"], today["balance_cents"]) == (
        "2026-10-31",
        False,
        100_000_000 + 1_000,
    )
    assert friday["closed"] is True


def test_t5b_only_the_collector_of_the_box_closes_it(flow, clock):
    _ready_to_close(flow, clock)

    assert flow.close_box(75_000, actor=ADMIN).status_code == 403
    assert flow.close_box(75_000, actor="cobrador-2").status_code == 403
    assert flow.close_box(75_000, actor="cobrador-2", collector="cobrador-2").status_code in (
        201,
        409,
    ), "another collector closes their own box by their own rules"
    assert _box(flow)["closed"] is False
    assert flow.close_box(75_000, actor="nadie", collector="nadie").status_code == 401


def test_t5b_sunday_has_no_box_to_close(flow, clock):
    clock.advance(timedelta(days=2))  # Sunday 1 November

    response = flow.close_box(0)

    assert response.status_code == 409
    assert response.json()["type"].endswith("/caja-no-disponible")
