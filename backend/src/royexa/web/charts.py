"""T11b: the geometry of the discrepancy bar chart. The server computes where each bar goes and
the template writes the SVG, so the chart needs no library and no script (T11b). A shortage
hangs below the axis and a surplus rises above it, on one scale for both."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from math import ceil

from royexa.closing.application import DayEvolution
from royexa.web.format import short_date

WIDTH = 360
MARGIN = 8
HALF = 70.0  # height of each half, above and below the axis
TOP = 6.0
MAX_BAR_WIDTH = 36.0
MIN_BAR = 1.5  # a non-zero amount is never invisible
TICK = 2.0  # an exact day is a hairline on the axis
MAX_LABELS = 6
LABEL_GAP = 16.0


@dataclass(frozen=True)
class Bar:
    x: float
    y: float
    width: float
    height: float
    kind: str  # short, surplus or none
    label: str


@dataclass(frozen=True)
class Label:
    x: float
    text: str


@dataclass(frozen=True)
class Chart:
    width: int
    height: int
    axis_y: float
    half_height: float
    left: float
    right: float
    bars: list[Bar]
    labels: list[Label]


def _bar_label(day: date, net: int, count: int, fmt: Callable[[int], str]) -> str:
    when = short_date(day)
    if net < 0:
        return f"{when}: faltan {fmt(-net)}"
    if net > 0:
        return f"{when}: sobran {fmt(net)}"
    if count:
        return f"{when}: {count} descuadres que se compensan"
    return f"{when}: sin descuadre"


def discrepancy_chart(days: list[DayEvolution], fmt: Callable[[int], str]) -> Chart | None:
    """One bar per collection day with the net difference; None when there is no day to draw."""
    if not days:
        return None
    largest = max(abs(day.net.cents) for day in days)
    axis_y = TOP + HALF
    slot = (WIDTH - 2 * MARGIN) / len(days)
    width = round(min(slot * 0.7, MAX_BAR_WIDTH), 1)
    bars, labels = [], []
    step = max(1, ceil(len(days) / MAX_LABELS))
    for index, day in enumerate(days):
        net = day.net.cents
        x = round(MARGIN + slot * index + (slot - width) / 2, 1)
        height = round(max(abs(net) / largest * HALF, MIN_BAR), 1) if net else TICK
        if net < 0:
            kind, y = "short", axis_y
        elif net > 0:
            kind, y = "surplus", round(axis_y - height, 1)
        else:
            kind, y = "none", round(axis_y - height / 2, 1)
        bars.append(Bar(x, y, width, height, kind, _bar_label(day.day, net, day.count, fmt)))
        if index % step == 0:
            labels.append(Label(round(x + width / 2, 1), day.day.strftime("%d/%m")))
    return Chart(
        width=WIDTH,
        height=round(axis_y + HALF + LABEL_GAP + 6),
        axis_y=axis_y,
        half_height=HALF,
        left=MARGIN,
        right=WIDTH - MARGIN,
        bars=bars,
        labels=labels,
    )
