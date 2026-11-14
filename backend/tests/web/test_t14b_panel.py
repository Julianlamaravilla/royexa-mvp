"""T14b (RF-07): the administrator's home is a panel: cards with the month's discrepancies,
the boxes left open and the failed notices, and two charts drawn by the server as SVG
(collected against disbursed by day, and the discrepancies). Runs on both adapters.
FakeClock starts on Friday 2026-10-30; the month is October 1 to 30."""

import re
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from support import ADMIN, COLLECTOR

from royexa.api import create_app
from royexa.closing.application import DayFlow
from royexa.seed import demo_password
from royexa.shared.money import Money
from royexa.web import charts, routes

STATIC = Path(routes.HERE) / "static"
HOME = "/web/admin"


def _browser(container, user: str = ADMIN) -> TestClient:
    browser = TestClient(create_app(container), follow_redirects=False)
    browser.post("/web/login", data={"user_id": user, "password": demo_password(user)})
    return browser


@pytest.fixture
def busy_month(flow, clock, notifier):
    """Thursday: a 1.000,00 disbursement and a box never closed. Friday: 600,00 in cash and
    100,00 by transfer, one failed notice, and a close 49,50 short."""
    clock.advance(-timedelta(days=1))
    flow.confirmed(client="cliente-1", amount_cents=100_000)
    clock.advance(timedelta(days=1))
    flow.pay("prestamo-impago", 60_000)
    flow.pay("prestamo-impago", 10_000, "TRANSFERENCIA")
    flow.dispatch()
    notifier.failing = True
    flow.approved(client="cliente-3")
    for _ in range(5):
        flow.dispatch()
    flow.visit_everyone()
    assert flow.close_box(55_050).status_code == 201
    return flow


def _svg(html: str, name: str) -> str:
    found = re.search(rf'<svg class="chart {name}".*?</svg>', html, re.S)
    assert found, f"no {name} on the page"
    return found.group(0)


def _bars(svg: str) -> list[tuple[str, float, float, float, float]]:
    """(kind, x, y, width, height) of each flow bar, in drawing order."""
    return [
        (kind, float(x), float(y), float(w), float(h))
        for kind, x, y, w, h in re.findall(
            r'<rect class="bar bar-(collected|disbursed)" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"',
            svg,
        )
    ]


# ---- the cards ----------------------------------------------------------------------------


def test_t14b_the_cards_count_the_discrepancies_the_open_boxes_and_the_failed_notices(
    container, busy_month
):
    html = _browser(container).get(HOME).text

    assert re.search(
        r'<a class="tile t-bad" href="/web/admin/descuadres"><strong>1</strong><span>Descuadres del mes</span>',
        html,
    )
    assert re.search(
        r'<a class="tile t-wait" href="/web/admin/descuadres"><strong>1</strong><span>Cajas sin cerrar</span>',
        html,
    )
    assert re.search(
        r'<a class="tile t-bad" href="/web/admin/avisos"><strong>1</strong><span>Avisos fallidos</span>',
        html,
    )


def test_t14b_the_discrepancy_card_says_how_much_is_missing_and_left_over(
    container, busy_month
):
    html = _browser(container).get(HOME).text

    assert "Faltantes 49,50" in html and "Sobrantes 0,00" in html


def test_t14b_a_quiet_month_shows_zeros_in_green_and_empty_states_instead_of_charts(
    container,
):
    html = _browser(container).get(HOME).text

    for label, href in (
        ("Descuadres del mes", "descuadres"),
        ("Cajas sin cerrar", "descuadres"),
        ("Avisos fallidos", "avisos"),
    ):
        assert re.search(
            rf'<a class="tile t-ok" href="/web/admin/{href}"><strong>0</strong><span>{label}</span>',
            html,
        ), label
    assert '<svg class="chart' not in html
    assert re.search(
        r'<div class="empty">.*Todavía no hay cobros ni desembolsos este mes',
        html,
        re.S,
    )
    assert re.search(r'<div class="empty">.*Sin descuadres este mes', html, re.S)


def test_t14b_the_home_keeps_the_menu_and_the_waiting_requests(container, flow):
    flow.requested(client="cliente-1")
    html = _browser(container).get(HOME).text

    for target in ("solicitudes", "libro", "clientes", "descuadres", "cajas", "avisos"):
        assert re.search(rf'<a class="card menu" href="/web/admin/{target}">', html), (
            target
        )
    assert "Solicitudes en espera (1)" in html
    assert 'name="ficha"' in html, "the logout form is still there"


# ---- the collected-against-disbursed chart ------------------------------------------------


def test_t14b_the_flow_chart_is_a_server_svg_with_a_viewbox_and_no_script(
    container, busy_month
):
    svg = _svg(_browser(container).get(HOME).text, "chart-flow")

    assert re.search(r'viewBox="0 0 360 \d+"', svg) and 'role="img"' in svg
    assert 'aria-labelledby="flow-title flow-desc"' in svg
    assert "width=" not in svg.split(">")[0], "the stylesheet sizes it"
    assert "<script" not in svg and "style=" not in svg and "<foreignObject" not in svg


def test_t14b_the_flow_chart_has_an_accessible_title_and_a_description_with_the_totals(
    container, busy_month
):
    svg = _svg(_browser(container).get(HOME).text, "chart-flow")

    title = re.search(r'<title id="flow-title">([^<]+)</title>', svg).group(1)
    desc = re.search(r'<desc id="flow-desc">([^<]+)</desc>', svg).group(1)
    assert "cobrado" in title.lower() and "desembolsado" in title.lower()
    assert "Cobrado 700,00" in desc and "Desembolsado 1.000,00" in desc
    assert "01/10/2026" in desc and "30/10/2026" in desc


def test_t14b_the_bars_are_proportional_and_sit_on_the_axis(container, busy_month):
    svg = _svg(_browser(container).get(HOME).text, "chart-flow")
    axis = float(
        re.search(r'<line class="axis" x1="[\d.]+" y1="([\d.]+)"', svg).group(1)
    )
    bars = _bars(svg)

    disbursed = next(b for b in bars if b[0] == "disbursed")
    collected = next(b for b in bars if b[0] == "collected")
    assert len(bars) == 2, "a day without money draws nothing"
    assert collected[4] / disbursed[4] == pytest.approx(70_000 / 100_000, rel=0.02)
    for _, _, y, _, height in bars:
        assert y + height == pytest.approx(axis), "every bar stands on the axis"
    assert disbursed[1] < collected[1], "Thursday comes before Friday"


def test_t14b_every_bar_names_its_day_and_amount_and_the_kinds_differ_by_more_than_colour(
    container, busy_month
):
    html = _browser(container).get(HOME).text
    svg = _svg(html, "chart-flow")
    css = (STATIC / "app.css").read_text()

    assert "29/10/2026: desembolsado 1.000,00" in svg
    assert "30/10/2026: cobrado 700,00" in svg
    collected = re.search(r"\.bar-collected\s*\{([^}]*)\}", css).group(1)
    disbursed = re.search(r"\.bar-disbursed\s*\{([^}]*)\}", css).group(1)
    assert "stroke" not in collected and "stroke" in disbursed, "solid against outlined"
    assert re.search(r'<li class="key-collected">Cobrado', html)
    assert re.search(r'<li class="key-disbursed">Desembolsado', html)


def test_t14b_the_flow_chart_has_a_scale_note_and_day_labels(container, busy_month):
    svg = _svg(_browser(container).get(HOME).text, "chart-flow")

    assert "1.000,00" in re.search(
        r'<text class="side"[^>]*>([^<]+)</text>', svg
    ).group(1)
    assert re.findall(r'<text class="tick"[^>]*>(\d\d/\d\d)</text>', svg), "day labels"


# ---- the discrepancy chart on the panel ---------------------------------------------------


def test_t14b_the_panel_also_draws_the_discrepancy_chart_of_the_month(
    container, busy_month
):
    html = _browser(container).get(HOME).text
    svg = re.search(r'<svg class="chart" .*?</svg>', html, re.S).group(0)

    assert 'aria-labelledby="chart-title chart-desc"' in svg
    assert "30/10/2026: faltan 49,50" in svg
    assert 'class="bar bar-short"' in svg and '<pattern id="hatch"' in svg


# ---- hygiene ------------------------------------------------------------------------------


def test_t14b_nothing_inline_and_every_icon_exists_and_nothing_external(
    container, busy_month
):
    html = _browser(container).get(HOME).text

    assert "<script>" not in html and "<style" not in html
    assert not re.search(r"\sstyle=|\sonclick=|\son[a-z]+=", html)
    assert not re.search(r'(src|href)="https?://', html)
    used = set(re.findall(r'<use href="#(i-[a-z-]+)"', html))
    defined = set(re.findall(r'<symbol id="(i-[a-z-]+)"', html))
    assert used and used <= defined, used - defined


def test_t14b_two_charts_on_one_page_do_not_share_an_id(container, busy_month):
    html = _browser(container).get(HOME).text

    ids = re.findall(r'\sid="([^"]+)"', html)
    assert len(ids) == len(set(ids)), "two charts on one page must not share an id"


def test_t14b_only_the_administrator_sees_the_panel(container):
    assert _browser(container, COLLECTOR).get(HOME).headers["location"] == "/web/ruta"
    anonymous = TestClient(create_app(container), follow_redirects=False)
    assert anonymous.get(HOME).headers["location"] == "/web/login"


# ---- the chart builder on its own ---------------------------------------------------------


def _flow(*rows: tuple[int, int]) -> list[DayFlow]:
    return [
        DayFlow(
            date(2026, 10, 1) + timedelta(days=n), Money(collected), Money(disbursed)
        )
        for n, (collected, disbursed) in enumerate(rows)
    ]


def _fmt(cents: int) -> str:
    return str(cents)


def test_t14b_the_builder_returns_nothing_when_no_money_moved():
    assert charts.flow_chart([], _fmt) is None
    assert charts.flow_chart(_flow((0, 0), (0, 0)), _fmt) is None


def test_t14b_the_builder_scales_both_series_on_one_scale():
    chart = charts.flow_chart(_flow((500, 1_000), (250, 0)), _fmt)

    heights = {
        (bar.kind, index): bar.height
        for index, day in enumerate((0, 1))
        for bar in chart.bars
        if bar.day == day
    }
    assert heights[("disbursed", 0)] == pytest.approx(charts.PLOT)
    assert heights[("collected", 0)] == pytest.approx(charts.PLOT / 2, abs=0.1)
    assert heights[("collected", 1)] == pytest.approx(charts.PLOT / 4, abs=0.1)
    assert ("disbursed", 1) not in heights, "no bar for zero"


def test_t14b_a_tiny_amount_is_never_invisible():
    chart = charts.flow_chart(_flow((1, 1_000_000)), _fmt)

    assert min(bar.height for bar in chart.bars) >= charts.MIN_BAR


@pytest.mark.parametrize("days", [1, 7, 26, 60, 366])
def test_t14b_the_bars_stay_inside_the_drawing_for_any_length(days):
    chart = charts.flow_chart(
        _flow(*[(n * 10 + 5, 1_000 - n) for n in range(days)]), _fmt
    )

    for bar in chart.bars:
        assert 0 <= bar.x and bar.x + bar.width <= chart.width
        assert 0 <= bar.y and bar.y + bar.height <= chart.axis_y + 0.01
    assert len(chart.labels) <= charts.MAX_LABELS
