"""How the pages write amounts and dates (T7-P1)."""

import re
from datetime import date
from fractions import Fraction

from royexa.loans.domain import exact_decimal

MONTHS = (
    "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre"
).split()
WEEKDAYS = "lunes martes miércoles jueves viernes sábado domingo".split()


def money(cents: int, symbol: str = "") -> str:
    """Two decimals and thousands in the Spanish style, 1.234,56. The currency is not known,
    so the symbol is empty unless one is configured; it goes after the sign."""
    whole, fraction = divmod(abs(cents), 100)
    number = f"{whole:,}".replace(",", ".") + f",{fraction:02d}"
    sign = "-" if cents < 0 else ""
    return f"{sign}{symbol} {number}" if symbol else f"{sign}{number}"


def weekday_name(day: date) -> str:
    return WEEKDAYS[day.weekday()][:3]


def long_date(day: date) -> str:
    return f"{WEEKDAYS[day.weekday()]} {day.day} de {MONTHS[day.month - 1]} de {day.year}"


def short_date(day: date) -> str:
    return day.strftime("%d/%m/%Y")


_AMOUNT = re.compile(r"(\d{1,3}(\.\d{3})+|\d+)(,\d{1,2})?")


def parse_amount(text: str) -> int | None:
    """What a person types in Spanish, 1.234,56 or 250,5 or 30, as cents; None when it is not
    clear. A dot is only a thousands separator and a comma the decimal mark, so 250.50 and
    1,234 are refused instead of read as another amount."""
    text = text.strip()
    if not _AMOUNT.fullmatch(text):
        return None
    whole, _, fraction = text.replace(".", "").partition(",")
    return int(whole) * 100 + int(fraction.ljust(2, "0") or 0)


def parse_signed_amount(text: str) -> int | None:
    """T14a: an amount with its sign, -25,00 or +10 or 1.000, as signed cents; None when it is
    not clear. No sign means positive. The caller refuses zero."""
    text = text.strip()
    sign = -1 if text.startswith("-") else 1
    cents = parse_amount(text[1:] if text[:1] in "+-" and text else text)
    return None if cents is None else sign * cents


def installments_text(value: Fraction) -> str:
    """The fractional counter in Spanish and never rounded (RN-01, T13): a finite decimal with
    a comma (19,5); when there is none, the whole part and the exact fraction (18 y 5/6)."""
    text = exact_decimal(value)
    if "/" not in text:
        return text.replace(".", ",")
    whole, rest = divmod(value.numerator, value.denominator)
    fraction = f"{rest}/{value.denominator}"
    return f"{whole} y {fraction}" if whole else fraction
