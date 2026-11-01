"""Money as integer cents (AD-05, ASR-04). Binary floats never represent money."""

from __future__ import annotations

from dataclasses import dataclass

from royexa.shared.errors import DomainError

BASIS_POINTS = 10_000


class InvalidAmount(DomainError):
    pass


@dataclass(frozen=True, order=True)
class Money:
    cents: int

    def __post_init__(self) -> None:
        if isinstance(self.cents, bool) or not isinstance(self.cents, int):
            raise InvalidAmount("money must be an integer number of cents")

    @property
    def is_positive(self) -> bool:
        return self.cents > 0

    def __add__(self, other: Money) -> Money:
        return Money(self.cents + other.cents)

    def __sub__(self, other: Money) -> Money:
        return Money(self.cents - other.cents)

    def __neg__(self) -> Money:
        return Money(-self.cents)

    def fraction_bps(self, basis_points: int) -> Money:
        """Share of this amount, rounded down to the cent."""
        return Money(self.cents * basis_points // BASIS_POINTS)

    def split(self, parts: int) -> list[Money]:
        """Equal parts; the last one absorbs the remainder so the sum stays exact."""
        if parts < 1:
            raise InvalidAmount("parts must be at least 1")
        share, remainder = divmod(self.cents, parts)
        return [Money(share)] * (parts - 1) + [Money(share + remainder)]
