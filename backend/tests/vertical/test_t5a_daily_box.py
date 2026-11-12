"""T5a, RN-02 and T5-P2: one cash box per collector and day, opened by the first movement.

Runs on both adapters (fixture `backend`) except the time-zone cases. FakeClock starts on
Friday 2026-10-30; the collector's float is 1,000,000.00 (100,000,000 cents).
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from support import ADMIN, COLLECTOR, FakeClock, Flow

from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.bootstrap import Settings, build_container

FLOAT = 100_000_000


def _box(flow, day: str | None = None, actor: str = COLLECTOR) -> dict:
    suffix = f"?date={day}" if day else ""
    response = flow._get(f"/v1/cash-boxes/{COLLECTOR}{suffix}", actor)
    assert response.status_code == 200, response.text
    return response.json()


def test_t5a_the_box_of_the_day_starts_at_the_collectors_float(flow):
    box = _box(flow)

    assert (box["day"], box["opening_balance_cents"], box["balance_cents"]) == (
        "2026-10-30",
        FLOAT,
        FLOAT,
    )
    assert box["closed"] is False


def test_t5a_the_first_movement_of_the_day_opens_the_box_for_that_day(flow):
    flow.confirmed()

    box = _box(flow)

    assert box["id"] == "caja-cobrador-1-2026-10-30"
    assert (box["opening_balance_cents"], box["balance_cents"]) == (FLOAT, FLOAT - 100_000)
    entry = flow.ledger()[0]
    assert entry["cash_box_id"] == box["id"]


def test_t5a_the_next_collection_day_opens_another_box_with_the_same_float(flow, clock):
    loan = flow.confirmed()["loan"]  # Friday: the float is spent by 100,000
    clock.advance(timedelta(days=1))  # Saturday 31 October

    fresh = _box(flow)
    assert (fresh["day"], fresh["opening_balance_cents"], fresh["balance_cents"]) == (
        "2026-10-31",
        FLOAT,
        FLOAT,
    )
    assert flow.pay(loan["id"], 3_000).status_code == 201

    saturday = _box(flow)
    friday = _box(flow, "2026-10-30")
    assert saturday["balance_cents"] == FLOAT + 3_000
    assert friday["balance_cents"] == FLOAT - 100_000
    assert friday["closed"] is False, "yesterday's box stays open: closing it is the collector's"
    assert saturday["id"] != friday["id"]


def test_t5a_a_payment_goes_to_the_box_of_the_day_it_was_registered(flow, clock):
    loan = flow.confirmed()["loan"]
    flow.pay(loan["id"], 3_000)
    clock.advance(timedelta(days=3))  # Monday 2 November
    flow.pay(loan["id"], 1_000)

    assert _box(flow, "2026-10-30")["balance_cents"] == FLOAT - 100_000 + 3_000
    assert _box(flow, "2026-11-02")["balance_cents"] == FLOAT + 1_000


def test_t5a_sunday_has_no_box_and_money_movements_are_refused(flow, clock):
    loan = flow.confirmed()["loan"]
    pending = flow.approved(client="cliente-3")
    code = flow.issued_code(pending["id"])
    clock.current = datetime(2026, 11, 1, 14, 0, tzinfo=UTC)  # Sunday

    assert flow._get(f"/v1/cash-boxes/{COLLECTOR}", COLLECTOR).status_code == 409
    refused_payment = flow.pay(loan["id"], 3_000)
    refused_confirmation = flow.confirm(pending["id"], code)

    for refused in (refused_payment, refused_confirmation):
        assert refused.status_code == 409
        assert refused.json()["type"].endswith("/caja-no-disponible")
    assert flow.read(pending["id"])["status"] == "APROBADO"
    assert flow._get(f"/v1/loans/{loan['id']}/payments").json() == []
    assert _box(flow, "2026-10-30")["balance_cents"] == FLOAT - 100_000


def test_t5a_a_day_without_movements_has_no_box_to_read_in_the_past(flow):
    response = flow._get(f"/v1/cash-boxes/{COLLECTOR}?date=2026-10-28", ADMIN)

    assert response.status_code == 409


def _flow_in_zone(zone: str, now: datetime) -> Flow:
    notifier = SimulatedNotifier()
    built = build_container(Settings(timezone=zone), FakeClock(now), notifier)
    return Flow(TestClient(create_app(built)), notifier)


# 03:00 UTC on Sunday 1 November is still Saturday 22:00 in Bogota.
SATURDAY_NIGHT_IN_BOGOTA = datetime(2026, 11, 1, 3, 0, tzinfo=UTC)


def test_t5a_in_utc_that_instant_is_sunday_with_no_box_and_nobody_pending():
    flow = _flow_in_zone("UTC", SATURDAY_NIGHT_IN_BOGOTA)

    assert flow._get(f"/v1/cash-boxes/{COLLECTOR}", COLLECTOR).status_code == 409
    assert flow.pending_clients() == []


def test_t5a_in_the_configured_zone_the_day_is_the_local_one_for_box_and_pending_visits():
    flow = _flow_in_zone("America/Bogota", SATURDAY_NIGHT_IN_BOGOTA)

    assert _box(flow)["day"] == "2026-10-31"
    assert flow.pending_clients() == ["cliente-2"]
    assert flow.pay("prestamo-impago", 1_000).status_code == 201
    assert _box(flow)["id"] == "caja-cobrador-1-2026-10-31"
    assert flow.pending_clients() == []
