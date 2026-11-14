"""T11b: the collector's forms and the administrator's pages use the visual system of T11a
(page head with a way back, cards, badges, bottom tabs, the stylesheet's form components),
nothing inline, every icon exists, and the discrepancy chart is an SVG drawn by the server whose
bars follow the amounts. Runs on both adapters. FakeClock starts on Friday 2026-10-30."""

import re
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from support import ADMIN, COLLECTOR

from royexa.api import create_app
from royexa.seed import demo_password
from royexa.web import charts, routes

STATIC = Path(routes.HERE) / "static"
PERIOD = "?desde=2026-10-30&hasta=2026-11-02"


def _browser(container, user: str) -> TestClient:
    browser = TestClient(create_app(container), follow_redirects=False)
    browser.post("/web/login", data={"user_id": user, "password": demo_password(user)})
    return browser


@pytest.fixture
def timeline(flow, clock):
    """Friday short by 49,50, Saturday over by 10,00, Sunday off, Monday exact."""
    flow.pay("prestamo-impago", 70_000)
    flow.close_box(65_050)
    clock.advance(timedelta(days=1))
    flow.close_box(1_000)
    clock.advance(timedelta(days=2))
    flow.close_box(0)
    return flow


def _collector_pages(container, flow) -> dict[str, str]:
    waiting = flow.requested(client="cliente-1")
    approved = flow.approved(client="cliente-3", amount_cents=20_000)
    browser = _browser(container, COLLECTOR)
    pages = {
        "pago": browser.get("/web/pago/prestamo-impago").text,
        "no-pago": browser.get("/web/no-pago/prestamo-impago").text,
        "solicitud": browser.get("/web/desembolso/nuevo").text,
        "desembolso-aprobado": browser.get(f"/web/desembolso/{approved['id']}").text,
        "desembolso-espera": browser.get(f"/web/desembolso/{waiting['id']}").text,
        "cierre-pendientes": browser.get("/web/cierre").text,
    }
    flow.visit_everyone()
    pages["cierre"] = browser.get("/web/cierre").text
    return pages


def _admin_pages(container, flow) -> dict[str, str]:
    flow.requested(client="cliente-1")
    browser = _browser(container, ADMIN)
    return {
        "admin": browser.get("/web/admin").text,
        "solicitudes": browser.get("/web/admin/solicitudes").text,
        "libro": browser.get("/web/admin/libro").text,
        "clientes": browser.get("/web/admin/clientes").text,
        "cajas": browser.get("/web/admin/cajas").text,
        "descuadres": browser.get("/web/admin/descuadres" + PERIOD).text,
    }


def _all_pages(container, flow) -> dict[str, str]:
    return {**_collector_pages(container, flow), **_admin_pages(container, flow)}


def test_t11b_no_page_has_inline_style_script_or_a_foreign_resource(container, flow):
    for name, html in _all_pages(container, flow).items():
        assert html.count('<link rel="stylesheet" href="/web/static/app.css">') == 1, name
        assert "style=" not in html and "<style" not in html, name
        assert "<script>" not in html and "onclick=" not in html and "onsubmit=" not in html, name
        assert not re.search(r"""(src|href)=["']https?://""", html), name


def test_t11b_every_icon_a_page_uses_exists_in_the_sprite(container, flow, timeline):
    pages = _all_pages(container, flow)
    for name, html in pages.items():
        used = set(re.findall(r'<use href="#(i-[a-z-]+)"', html))
        defined = set(re.findall(r'<symbol id="(i-[a-z-]+)"', html))
        assert used <= defined, f"{name}: {used - defined}"
        assert used, f"{name}: the page shows no icon at all"


def test_t11b_every_page_has_a_head_with_a_way_back_and_one_main_title(container, flow):
    for name, html in _all_pages(container, flow).items():
        if name == "admin":
            continue
        assert re.search(r'<div class="page-head">\s*<a class="back" href="/web/[a-z/]*">', html), name
        assert html.count("<h1") == 1, name
    assert 'class="page-head"' not in _admin_pages(container, flow)["admin"]


def test_t11b_the_collector_forms_use_the_form_components_and_the_tabs(container, flow):
    pages = _collector_pages(container, flow)
    for name in ("pago", "no-pago", "solicitud", "desembolso-aprobado", "cierre"):
        html = pages[name]
        assert re.search(r'<form method="post" action="[^"]+" class="stack">', html), name
        assert re.search(r'<button type="submit" class="primary">', html), name
        assert "<label" in html and 'name="ficha"' in html, name
        assert '<nav class="tabs"' in html and 'class="has-tabs"' in html, name
    assert 'href="/web/no-pago/prestamo-impago"' in pages["pago"]
    assert 'aria-current="page"' in pages["cierre"] and 'href="/web/cierre"' in pages["cierre"]
    assert re.search(r'<a href="/web/desembolso/nuevo" aria-current="page">', pages["solicitud"])


def test_t11b_the_collector_forms_say_what_each_field_expects(container, flow):
    pages = _collector_pages(container, flow)

    assert 'class="hint"' in pages["pago"] and "1.234,56" in pages["pago"]
    assert 'class="hint"' in pages["cierre"] and "1.234,56" in pages["cierre"]
    assert 'class="hint"' in pages["solicitud"]
    assert 'class="card"' in pages["pago"] and "Saldo" in pages["pago"]


def test_t11b_the_status_of_a_disbursement_is_a_badge_not_loose_text(container, flow):
    pages = _collector_pages(container, flow)

    assert '<span class="badge badge-wait">En espera</span>' in pages["desembolso-espera"]
    assert '<span class="badge badge-info">Aprobado</span>' in pages["desembolso-aprobado"]


def test_t11b_the_pending_clients_of_the_close_page_are_cards_with_their_initials(container, flow):
    html = _collector_pages(container, flow)["cierre-pendientes"]

    assert "Aún hay clientes pendientes" in html and "<form" not in html.split("<main", 1)[1]
    assert re.search(r'<li class="card">\s*<div class="row">\s*<span class="avatar" aria-hidden="true">', html)


def test_t11b_the_admin_pages_share_one_tab_bar_that_marks_the_current_page(container, flow):
    pages = _admin_pages(container, flow)
    current = {
        "solicitudes": "/web/admin/solicitudes",
        "libro": "/web/admin/libro",
        "clientes": "/web/admin/clientes",
        "cajas": "/web/admin/cajas",
        "descuadres": "/web/admin/descuadres",
    }
    for name, href in current.items():
        html = pages[name]
        assert '<nav class="tabs" aria-label="Administración">' in html, name
        assert 'class="has-tabs"' in html, name
        marked = re.findall(r'<a href="([^"]+)" aria-current="page">', html)
        assert marked == [href], (name, marked)
        for target in current.values():
            assert f'href="{target}"' in html, (name, target)
    assert '<nav class="tabs" aria-label="Administración">' in pages["admin"]
    assert "aria-current" not in pages["admin"]


def test_t11b_the_admin_home_offers_every_page_as_a_card_with_an_icon(container, flow):
    html = _admin_pages(container, flow)["admin"]

    for target in ("solicitudes", "libro", "clientes", "descuadres", "cajas"):
        assert re.search(rf'<a class="card menu" href="/web/admin/{target}[^"]*">\s*<svg class="icon"', html), target
    assert "Solicitudes en espera (1)" in html


def test_t11b_the_requests_page_shows_each_request_as_a_card_with_its_two_forms(container, flow):
    html = _admin_pages(container, flow)["solicitudes"]

    assert 'class="card"' in html and '<span class="avatar"' in html
    assert '<button type="submit" class="primary">Aprobar</button>' in html
    assert '<button type="submit">Rechazar</button>' in html
    assert 'class="badge badge-wait"' in html


def test_t11b_the_ledger_marks_money_in_and_money_out_with_a_sign_and_a_class(container, flow):
    flow.pay("prestamo-impago", 20_000)
    flow.confirmed(client="cliente-3", amount_cents=30_000)
    html = _browser(container, ADMIN).get("/web/admin/libro").text

    assert re.search(r'class="amount amount-in">\+', html), "cash in carries a plus sign"
    assert 'class="amount amount-out">' in html
    assert 'class="badge badge-ok"' in html and "PAGO" in html
    assert re.search(r'class="badge badge-[a-z]+">DESEMBOLSO', html)


def test_t11b_an_empty_list_is_a_card_with_a_message_not_bare_text(container):
    browser = _browser(container, ADMIN)

    for path, words in (
        ("/web/admin/solicitudes", "No hay solicitudes en espera."),
        ("/web/admin/libro", "El libro está vacío."),
        ("/web/admin/cajas", "Todavía no hay cajas cerradas."),
    ):
        html = browser.get(path).text
        assert re.search(rf'<div class="empty">.*{re.escape(words)}', html, re.S), path


def test_t11b_the_clients_show_their_initials_and_their_route(container):
    html = _browser(container, ADMIN).get("/web/admin/clientes").text

    assert '<span class="avatar" aria-hidden="true">' in html
    assert re.search(r'class="badge badge-info">ruta-1<', html)


def test_t11b_the_closed_boxes_show_their_result_with_a_badge(timeline, container):
    html = _browser(container, ADMIN).get("/web/admin/cajas").text

    assert 'class="badge badge-bad"' in html, "a shortage"
    assert 'class="badge badge-ok"' in html, "a surplus or an exact count"
    assert "Faltan 49,50" in html and "Sobran 10,00" in html and "Sin descuadre" in html


# --- the discrepancy chart ---------------------------------------------------------------


def _chart(html: str) -> str:
    found = re.search(r'<svg class="chart".*?</svg>', html, re.S)
    assert found, "no chart on the page"
    return found.group(0)


def _bars(svg: str) -> list[tuple[str, float, float]]:
    """(kind, y, height) of every bar, in the order they were drawn."""
    return [
        (kind, float(y), float(height))
        for kind, y, height in re.findall(
            r'<rect class="bar bar-(short|surplus|none)" x="[\d.]+" y="([\d.]+)" width="[\d.]+" height="([\d.]+)"', svg
        )
    ]


def test_t11b_the_chart_is_an_svg_from_the_server_that_scales_to_a_phone(timeline, container):
    html = _browser(container, ADMIN).get("/web/admin/descuadres" + PERIOD).text
    svg = _chart(html)

    assert re.search(r'viewBox="0 0 360 \d+"', svg)
    assert 'role="img"' in svg and "width=" not in svg.split(">")[0], "the stylesheet sizes it"
    assert "<script" not in svg and "style=" not in svg and "<foreignObject" not in svg
    rule = re.search(r"\.chart\s*\{([^}]*)\}", (STATIC / "app.css").read_text()).group(1)
    assert "width: 100%" in rule and "height: auto" in rule


def test_t11b_the_chart_has_an_accessible_title_and_a_description_with_the_facts(timeline, container):
    svg = _chart(_browser(container, ADMIN).get("/web/admin/descuadres" + PERIOD).text)

    title = re.search(r'<title id="chart-title">([^<]+)</title>', svg)
    desc = re.search(r'<desc id="chart-desc">([^<]+)</desc>', svg)
    assert title and desc
    assert 'aria-labelledby="chart-title chart-desc"' in svg
    assert "descuadres" in title.group(1).lower()
    assert "2 descuadres" in desc.group(1) and "49,50" in desc.group(1) and "10,00" in desc.group(1)


def test_t11b_a_shortage_hangs_below_the_axis_and_a_surplus_rises_above_it(timeline, container):
    svg = _chart(_browser(container, ADMIN).get("/web/admin/descuadres" + PERIOD).text)
    axis = float(re.search(r'<line class="axis" x1="[\d.]+" y1="([\d.]+)"', svg).group(1))
    bars = {kind: (y, height) for kind, y, height in _bars(svg)}

    short_y, short_h = bars["short"]
    surplus_y, surplus_h = bars["surplus"]
    assert short_y == pytest.approx(axis), "a shortage starts at the axis and goes down"
    assert surplus_y + surplus_h == pytest.approx(axis), "a surplus ends at the axis, rising"
    assert short_h > 0 and surplus_h > 0


def test_t11b_the_bars_are_proportional_to_the_amounts(timeline, container):
    svg = _chart(_browser(container, ADMIN).get("/web/admin/descuadres" + PERIOD).text)
    bars = {kind: height for kind, _, height in _bars(svg)}

    assert bars["short"] / bars["surplus"] == pytest.approx(4_950 / 1_000, rel=0.02)


def test_t11b_the_kinds_differ_by_class_and_by_a_pattern_not_only_by_colour(timeline, container):
    html = _browser(container, ADMIN).get("/web/admin/descuadres" + PERIOD).text
    css = (STATIC / "app.css").read_text()

    assert 'class="bar bar-short"' in html and 'class="bar bar-surplus"' in html
    assert '<pattern id="hatch"' in html, "the shortage is hatched"
    short_rule = re.search(r"\.bar-short\s*\{([^}]*)\}", css).group(1)
    surplus_rule = re.search(r"\.bar-surplus\s*\{([^}]*)\}", css).group(1)
    assert "url(#hatch)" in short_rule and "url(#hatch)" not in surplus_rule
    assert "var(--bad)" in short_rule and "var(--ok)" in surplus_rule


def test_t11b_every_bar_names_its_day_and_amount_for_who_points_at_it(timeline, container):
    svg = _chart(_browser(container, ADMIN).get("/web/admin/descuadres" + PERIOD).text)

    assert "30/10/2026: faltan 49,50" in svg
    assert "31/10/2026: sobran 10,00" in svg
    assert "02/11/2026: sin descuadre" in svg


def test_t11b_a_key_explains_the_two_kinds_without_numbers(timeline, container):
    html = _browser(container, ADMIN).get("/web/admin/descuadres" + PERIOD).text

    assert re.search(r'<li class="key-short">.*Faltante.*abajo', html, re.S)
    assert re.search(r'<li class="key-surplus">.*Sobrante.*arriba', html, re.S)


def test_t11b_with_no_discrepancies_the_chart_gives_way_to_an_empty_state(flow, container):
    flow.pay("prestamo-impago", 70_000)
    flow.close_box(70_000)

    html = _browser(container, ADMIN).get("/web/admin/descuadres" + PERIOD).text

    assert "No hubo descuadres en el periodo" in html
    assert '<svg class="chart"' not in html
    assert re.search(r'<div class="empty">.*Sin descuadres', html, re.S)


def test_t11b_the_chart_keeps_to_the_viewbox_whatever_the_length_of_the_period(container, flow):
    flow.pay("prestamo-impago", 70_000)
    flow.close_box(65_050)

    html = _browser(container, ADMIN).get("/web/admin/descuadres?desde=2026-08-01&hasta=2026-11-02").text
    svg = _chart(html)

    for x, width in re.findall(r'<rect class="bar [^"]+" x="([\d.]+)" y="[\d.]+" width="([\d.]+)"', svg):
        assert 0 <= float(x) and float(x) + float(width) <= 360


def test_t11b_the_period_error_still_shows_in_spanish_without_a_chart(container):
    html = _browser(container, ADMIN).get("/web/admin/descuadres?desde=2026-11-02&hasta=2026-10-30").text

    assert 'role="alert"' in html and '<svg class="chart"' not in html


# --- the chart builder on its own ---------------------------------------------------------


def _days(*nets: int):
    from datetime import date

    from royexa.closing.application import DayEvolution
    from royexa.shared.money import Money

    return [
        DayEvolution(day=date(2026, 10, 26) + timedelta(days=index), count=int(net != 0), net=Money(net))
        for index, net in enumerate(nets)
    ]


def _fmt(cents: int) -> str:
    return f"{cents / 100:.2f}"


def test_t11b_builder_heights_follow_the_amounts_and_the_largest_fills_its_half():
    chart = charts.discrepancy_chart(_days(-10_000, 5_000, 0, 2_500), _fmt)

    heights = [bar.height for bar in chart.bars]
    assert heights[0] == pytest.approx(chart.half_height)
    assert heights[1] == pytest.approx(heights[0] / 2)
    assert heights[3] == pytest.approx(heights[0] / 4)
    assert [bar.kind for bar in chart.bars] == ["short", "surplus", "none", "surplus"]


def test_t11b_builder_gives_an_exact_day_a_visible_tick_and_never_a_negative_height():
    chart = charts.discrepancy_chart(_days(0, -1, 100_000_000), _fmt)

    assert all(bar.height > 0 for bar in chart.bars)
    assert chart.bars[0].kind == "none"


def test_t11b_builder_labels_stay_few_so_they_do_not_overlap():
    chart = charts.discrepancy_chart(_days(*([-100] * 60)), _fmt)

    assert 1 <= len(chart.labels) <= 8
    assert len(chart.bars) == 60


def test_t11b_builder_has_nothing_to_draw_without_days():
    assert charts.discrepancy_chart([], _fmt) is None
