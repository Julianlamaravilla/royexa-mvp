"""T5a, T5-P3: the day, in the pilot's time zone, and the collection days."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfoNotFoundError

import pytest

from royexa.shared.calendar import BusinessCalendar


def test_t5a_the_day_defaults_to_utc():
    calendar = BusinessCalendar.in_zone("UTC")

    assert calendar.day_of(datetime(2026, 10, 31, 2, 0, tzinfo=UTC)) == date(2026, 10, 31)


def test_t5a_the_day_changes_at_the_local_midnight():
    bogota = BusinessCalendar.in_zone("America/Bogota")  # UTC-5, no daylight saving time

    assert bogota.day_of(datetime(2026, 10, 31, 4, 59, tzinfo=UTC)) == date(2026, 10, 30)
    assert bogota.day_of(datetime(2026, 10, 31, 5, 0, tzinfo=UTC)) == date(2026, 10, 31)


def test_t5a_monday_to_saturday_are_collection_days_and_sunday_is_not():
    calendar = BusinessCalendar.in_zone("UTC")

    assert [calendar.is_collection_day(date(2026, 10, day)) for day in range(26, 32)] == [True] * 6
    assert calendar.is_collection_day(date(2026, 11, 1)) is False  # Sunday


def test_t5a_an_unknown_zone_fails_at_start_instead_of_silently_using_utc():
    with pytest.raises(ZoneInfoNotFoundError):
        BusinessCalendar.in_zone("Nowhere/Land")
