"""T9 (RF-07, CA-13, T9-P1 to T9-P4): the administrator reads the cash discrepancies of a
period. Runs on both adapters.

The timeline, from Friday 2026-10-30 (the collector's box closes with a shortage), through
Saturday (a surplus) to Monday 2 November (an exact close, which is not a discrepancy). On
Friday cobrador-2 also moves cash and never closes its box.
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from support import COLLECTOR

from royexa.api import create_app

OTHER = "cobrador-2"


@pytest.fixture
def timeline(flow, clock):
    # Friday: 700,00 collected in cash, 650,50 delivered -> 49,50 missing.
    assert flow.pay("prestamo-impago", 70_000).status_code == 201
    assert flow.close_box(65_050).status_code == 201
    # Friday, route 2: a confirmed disbursement and no close.
    loan = flow.requested(actor=OTHER, client="cliente-4")
    assert flow.approve(loan["id"]).status_code == 200
    assert flow.confirm(loan["id"], flow.issued_code(loan["id"]), actor=OTHER).status_code == 200
    # Saturday: nothing expected, 10,00 delivered -> 10,00 left over.
    clock.advance(timedelta(days=1))
    assert flow.close_box(1_000).status_code == 201
    # Monday: nothing expected, nothing delivered -> no discrepancy.
    clock.advance(timedelta(days=2))
    assert flow.close_box(0).status_code == 201
    return flow


def _report(flow, query: str = "", actor: str = "admin-1"):
    return flow._get(f"/v1/cash-discrepancies{query}", actor)


def test_ca13_the_period_counts_the_discrepancies_and_details_each_one(timeline):
    response = _report(timeline, "?desde=2026-10-30&hasta=2026-11-02")

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["desde"], body["hasta"]) == ("2026-10-30", "2026-11-02")
    assert body["count"] == 2
    assert body["shortage_cents"] == 4_950 and body["surplus_cents"] == 1_000
    assert [(i["day"], i["collector_id"], i["discrepancy_cents"]) for i in body["items"]] == [
        ("2026-10-30", COLLECTOR, -4_950),
        ("2026-10-31", COLLECTOR, 1_000),
    ]
    assert body["items"][0]["expected_cents"] == 70_000
    assert body["items"][0]["delivered_cents"] == 65_050


def test_t9_p2_the_evolution_has_one_row_per_collection_day_including_the_quiet_ones(timeline):
    body = _report(timeline, "?desde=2026-10-30&hasta=2026-11-02").json()

    assert body["days"] == [
        {"day": "2026-10-30", "count": 1, "net_cents": -4_950},
        {"day": "2026-10-31", "count": 1, "net_cents": 1_000},
        {"day": "2026-11-02", "count": 0, "net_cents": 0},
    ], "Sunday is not a collection day and an exact close is not a discrepancy"


def test_t9_p1_the_range_is_inclusive_and_filters_by_the_day_of_the_close(timeline):
    saturday = _report(timeline, "?desde=2026-10-31&hasta=2026-10-31").json()
    friday = _report(timeline, "?desde=2026-10-30&hasta=2026-10-30").json()

    assert saturday["count"] == 1 and saturday["items"][0]["day"] == "2026-10-31"
    assert friday["count"] == 1 and friday["items"][0]["day"] == "2026-10-30"
    assert [d["day"] for d in saturday["days"]] == ["2026-10-31"]


def test_t9_p1_without_dates_the_period_is_the_current_month_up_to_today(timeline):
    body = _report(timeline).json()  # today is Monday 2 November

    assert (body["desde"], body["hasta"]) == ("2026-11-01", "2026-11-02")
    assert body["count"] == 0
    assert [d["day"] for d in body["days"]] == ["2026-11-02"]


def test_t9_p3_a_box_left_open_on_a_past_day_is_listed_apart_and_is_not_a_discrepancy(timeline):
    body = _report(timeline, "?desde=2026-10-30&hasta=2026-11-02").json()

    assert body["unclosed"] == [
        {"day": "2026-10-30", "collector_id": OTHER, "cash_box_id": f"caja-{OTHER}-2026-10-30"}
    ]
    assert all(item["collector_id"] != OTHER for item in body["items"])


def test_t9_p3_the_box_of_today_is_not_unclosed_yet(flow):
    flow.pay("prestamo-impago", 10_000)

    body = _report(flow, "?desde=2026-10-30&hasta=2026-10-30").json()

    assert body["unclosed"] == [] and body["count"] == 0


def test_t9_an_empty_period_reports_zeros(flow):
    body = _report(flow, "?desde=2026-10-01&hasta=2026-10-15").json()

    assert body["count"] == 0 and body["items"] == [] and body["unclosed"] == []
    assert body["shortage_cents"] == 0 and body["surplus_cents"] == 0
    assert all(day["count"] == 0 for day in body["days"]) and len(body["days"]) == 13


@pytest.mark.parametrize(
    "query",
    [
        "?desde=2026-11-02&hasta=2026-10-30",
        "?desde=2024-01-01&hasta=2026-10-30",
        "?desde=ayer&hasta=2026-10-30",
    ],
)
def test_t9_a_bad_period_is_refused(flow, query):
    response = _report(flow, query)

    assert response.status_code == 422, response.text


def test_t9_an_inverted_or_too_long_period_says_why(flow):
    inverted = _report(flow, "?desde=2026-11-02&hasta=2026-10-30")
    too_long = _report(flow, "?desde=2024-01-01&hasta=2026-10-30")

    assert inverted.json()["type"].endswith("/periodo-invalido")
    assert too_long.json()["type"].endswith("/periodo-invalido")


def test_t9_only_the_administrator_reads_it(flow, container):
    assert _report(flow, actor=COLLECTOR).status_code == 403
    assert TestClient(create_app(container)).get("/v1/cash-discrepancies").status_code == 401
