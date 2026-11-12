"""T5d, CA-08 and T5-P4: an error is corrected with a new compensating entry, never by
touching the original. Only an administrator; the motive is required; the entry lands in
the original collector's box of the day it is registered. Runs on both adapters.

FakeClock starts on Friday 2026-10-30.
"""

from datetime import timedelta

from support import ADMIN, COLLECTOR


def _wrong_payment(flow, clock) -> tuple[dict, dict]:
    """A client with a loan from yesterday and a cash payment of 30,000 recorded today."""
    clock.advance(-timedelta(days=1))
    client = flow._post("/v1/clients", ADMIN, {"name": "Cliente del error", "route_id": "ruta-1"})
    loan = flow.confirmed(client=client.json()["id"])["loan"]
    clock.advance(timedelta(days=1))
    payment = flow.pay(loan["id"], 30_000).json()["payment"]
    return loan, flow.payment_entry(payment["id"])


def _box(flow, day: str | None = None, collector: str = COLLECTOR) -> dict:
    suffix = f"?date={day}" if day else ""
    return flow._get(f"/v1/cash-boxes/{collector}{suffix}", ADMIN).json()


def test_ca08_the_correction_leaves_the_original_and_a_visible_compensating_entry(flow, clock):
    _, original = _wrong_payment(flow, clock)

    response = flow.adjust(original["id"], -2_500)

    assert response.status_code == 201, response.text
    adjustment = response.json()
    assert adjustment["entry_type"] == "AJUSTE"
    assert (adjustment["amount_cents"], adjustment["cash_effect_cents"]) == (-2_500, -2_500)
    assert adjustment["adjusts_entry_id"] == original["id"]
    assert adjustment["reason"] == "error de captura del importe"
    assert adjustment["actor_id"] == ADMIN
    assert (adjustment["disbursement_id"], adjustment["payment_id"]) == (None, None)
    assert adjustment["id"] != original["id"]
    entries = {entry["id"]: entry for entry in flow.ledger()}
    assert entries[original["id"]] == original, "the original is exactly as it was"
    assert entries[adjustment["id"]] == adjustment


def test_ca08_the_adjustment_moves_the_box_of_the_day_by_its_signed_amount(flow, clock):
    _, original = _wrong_payment(flow, clock)
    before = _box(flow)["balance_cents"]

    flow.adjust(original["id"], -2_500)
    assert _box(flow)["balance_cents"] == before - 2_500
    flow.adjust(original["id"], 1_000)

    assert _box(flow)["balance_cents"] == before - 1_500


def test_ca08_an_original_can_be_corrected_more_than_once_and_so_can_a_correction(flow, clock):
    _, original = _wrong_payment(flow, clock)
    first = flow.adjust(original["id"], -2_500).json()

    second = flow.adjust(original["id"], 500)
    third = flow.adjust(first["id"], 2_500)

    assert second.status_code == 201 and third.status_code == 201
    assert third.json()["adjusts_entry_id"] == first["id"]
    assert [e["entry_type"] for e in flow.ledger()].count("AJUSTE") == 3


def test_rn02_after_the_close_the_correction_waits_for_the_next_day_and_is_a_new_entry(
    flow, clock
):
    _, original = _wrong_payment(flow, clock)
    flow.visit_everyone()
    closed = flow.close_box(30_000).json()
    friday_balance = _box(flow)["balance_cents"]

    refused = flow.adjust(original["id"], -2_500)
    assert refused.status_code == 409
    assert refused.json()["type"].endswith("/caja-cerrada")
    assert [e["entry_type"] for e in flow.ledger()].count("AJUSTE") == 0

    clock.advance(timedelta(days=1))  # Saturday: a fresh box
    adjustment = flow.adjust(original["id"], -2_500)

    assert adjustment.status_code == 201
    assert adjustment.json()["cash_box_id"] == "caja-cobrador-1-2026-10-31"
    assert _box(flow, "2026-10-30")["balance_cents"] == friday_balance, "the closed box is untouched"
    assert flow.cash_closes().json() == [closed], "so is its close"
    assert _box(flow)["balance_cents"] == 100_000_000 - 2_500


def test_t5p1_the_adjustment_counts_in_the_expected_cash_of_the_day_it_lands(flow, clock):
    _, original = _wrong_payment(flow, clock)
    flow.visit_everyone()
    flow.close_box(30_000)
    clock.advance(timedelta(days=1))
    flow.adjust(original["id"], -2_500)
    flow.visit_everyone()

    closed = flow.close_box(0).json()

    assert closed["expected_cents"] == -2_500
    assert closed["discrepancy_cents"] == 2_500


def test_t5d_the_entry_lands_in_the_box_of_the_collector_who_owns_the_original(flow):
    disbursement = flow.approved(client="cliente-4", actor="cobrador-2")
    code = flow.issued_code(disbursement["id"])
    assert flow.confirm(disbursement["id"], code, actor="cobrador-2").status_code == 200
    original = flow.ledger(disbursement["id"])[0]

    adjustment = flow.adjust(original["id"], 5_000).json()

    assert adjustment["cash_box_id"] == original["cash_box_id"]
    assert adjustment["cash_box_id"] == "caja-cobrador-2-2026-10-30"
    assert _box(flow, collector="cobrador-1")["balance_cents"] == 100_000_000, "not this one"


def test_t5d_only_an_administrator_registers_a_correction(flow, clock):
    _, original = _wrong_payment(flow, clock)

    assert flow.adjust(original["id"], -2_500, actor=COLLECTOR).status_code == 403
    assert flow.adjust(original["id"], -2_500, actor="nadie").status_code == 401
    assert [e["entry_type"] for e in flow.ledger()].count("AJUSTE") == 0


def test_t5d_the_motive_is_required_and_the_amount_is_never_zero(flow, clock):
    _, original = _wrong_payment(flow, clock)

    for reason in ("", "   ", None):
        assert flow.adjust(original["id"], -2_500, reason=reason).status_code == 422, reason
    assert flow.adjust(original["id"], 0).status_code == 422
    assert [e["entry_type"] for e in flow.ledger()].count("AJUSTE") == 0


def test_t5d_an_unknown_entry_is_not_found(flow):
    response = flow.adjust("no-existe", 1_000)

    assert response.status_code == 404
    assert response.json()["type"].endswith("/asiento-no-encontrado")


def test_t5d_sunday_has_no_box_to_receive_the_correction(flow, clock):
    _, original = _wrong_payment(flow, clock)
    clock.advance(timedelta(days=2))  # Sunday 1 November

    response = flow.adjust(original["id"], -2_500)

    assert response.status_code == 409
    assert response.json()["type"].endswith("/caja-no-disponible")
