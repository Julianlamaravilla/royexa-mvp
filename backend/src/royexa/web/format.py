"""How the pages write amounts and dates (T7-P1)."""

from datetime import date

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


def long_date(day: date) -> str:
    return f"{WEEKDAYS[day.weekday()]} {day.day} de {MONTHS[day.month - 1]} de {day.year}"


def short_date(day: date) -> str:
    return day.strftime("%d/%m/%Y")
