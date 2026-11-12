"""T7a, T7-P1: amounts as 1.234,56 without a currency symbol unless one is configured."""

from datetime import date

import pytest

from royexa.web.format import long_date, money


@pytest.mark.parametrize(
    ("cents", "text"),
    [
        (0, "0,00"),
        (5, "0,05"),
        (99, "0,99"),
        (100, "1,00"),
        (123_456, "1.234,56"),
        (100_000_000, "1.000.000,00"),
        (70_000, "700,00"),
        (-250, "-2,50"),
        (-123_456, "-1.234,56"),
    ],
)
def test_t7a_amounts_have_two_decimals_and_thousands_in_the_spanish_style(cents, text):
    assert money(cents) == text


def test_t7a_a_configured_symbol_goes_in_front_after_the_sign():
    assert money(123_456, "$") == "$ 1.234,56"
    assert money(-250, "$") == "-$ 2,50"


def test_t7a_no_symbol_by_default_because_the_currency_is_not_known():
    assert money(123_456, "") == "1.234,56"


def test_t7a_dates_read_in_spanish():
    assert long_date(date(2026, 10, 30)) == "viernes 30 de octubre de 2026"
    assert long_date(date(2026, 11, 1)) == "domingo 1 de noviembre de 2026"
