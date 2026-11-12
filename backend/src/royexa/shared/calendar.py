"""The business day (T5-P3): one time zone for the pilot, and the days the collector works."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, tzinfo
from zoneinfo import ZoneInfo

SUNDAY = 7


@dataclass(frozen=True)
class BusinessCalendar:
    zone: tzinfo

    @classmethod
    def in_zone(cls, name: str) -> BusinessCalendar:
        """Raises ZoneInfoNotFoundError for an unknown name: a typo fails at start-up."""
        return cls(ZoneInfo(name))

    def day_of(self, instant: datetime) -> date:
        return instant.astimezone(self.zone).date()

    @staticmethod
    def is_collection_day(day: date) -> bool:
        """Monday to Saturday (CA-09, T3-P1)."""
        return day.isoweekday() != SUNDAY
