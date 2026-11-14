"""T14b: what was collected against what was disbursed, by collection day (the second chart of
the administrator's panel). A read-only query over the ledger; both adapters. FakeClock starts
on Friday 2026-10-30; Sunday 2026-11-01 is not a collection day."""

from datetime import date, timedelta

import pytest

from royexa.cash_box.domain import InvalidPeriod


def _report(container, since=None, until=None):
    return container.cash_flow_queries.report(since, until)


def _rows(report):
    return [
        (d.day.isoformat(), d.collected.cents, d.disbursed.cents) for d in report.days
    ]


def test_t14b_each_day_adds_what_was_collected_and_what_was_disbursed(
    flow, container, clock
):
    flow.confirmed(client="cliente-1", amount_cents=100_000)
    flow.pay("prestamo-impago", 30_000)
    flow.pay("prestamo-impago", 10_000, "TRANSFERENCIA")
    clock.advance(timedelta(days=1))
    flow.pay("prestamo-impago", 5_000)

    report = _report(container, date(2026, 10, 29), date(2026, 11, 2))

    assert _rows(report) == [
        ("2026-10-29", 0, 0),
        ("2026-10-30", 40_000, 100_000),
        ("2026-10-31", 5_000, 0),
        ("2026-11-02", 0, 0),
    ], "cash and transfers are collected; Sunday is not a collection day"
    assert (report.collected.cents, report.disbursed.cents) == (45_000, 100_000)
    assert (report.since, report.until) == (date(2026, 10, 29), date(2026, 11, 2))


def test_t14b_adjustments_and_expired_attempts_are_not_collected_or_disbursed(
    flow, container, clock
):
    flow.confirmed(client="cliente-1", amount_cents=100_000)
    payment = flow.pay("prestamo-impago", 30_000).json()["payment"]
    assert (
        flow.adjust(flow.payment_entry(payment["id"])["id"], -5_000).status_code == 201
    )
    expired = flow.approved(client="cliente-3")
    code = flow.issued_code(expired["id"])
    clock.advance(timedelta(minutes=61))
    flow.confirm(expired["id"], code)

    report = _report(container, date(2026, 10, 30), date(2026, 10, 30))

    assert _rows(report) == [("2026-10-30", 30_000, 100_000)]


def test_t14b_without_dates_the_period_is_the_month_up_to_today_like_the_discrepancies(
    container,
):
    report = _report(container)

    assert (report.since, report.until) == (date(2026, 10, 1), date(2026, 10, 30))
    assert len(report.days) == 26, "October 1 to 30 without its four Sundays"
    assert report.collected.cents == 0 and report.disbursed.cents == 0


def test_t14b_an_inverted_period_is_refused(container):
    with pytest.raises(InvalidPeriod):
        _report(container, date(2026, 10, 30), date(2026, 10, 1))
    with pytest.raises(InvalidPeriod):
        _report(container, date(2025, 1, 1), date(2026, 10, 30))


def test_t14b_the_other_routes_money_counts_too(flow, container):
    loan = flow.requested(actor="cobrador-2", client="cliente-4", amount_cents=70_000)
    assert flow.approve(loan["id"]).status_code == 200
    code = flow.issued_code(loan["id"])
    assert flow.confirm(loan["id"], code, actor="cobrador-2").status_code == 200

    assert _rows(_report(container, date(2026, 10, 30), date(2026, 10, 30))) == [
        ("2026-10-30", 0, 70_000)
    ]
