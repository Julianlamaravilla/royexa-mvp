"""What the pages say when the domain refuses something. T7b to T7d add their cases."""

from royexa.shared.errors import DomainError

GENERIC = "No se pudo completar la operación."

_MESSAGES: dict[type[DomainError], str] = {}


def describe(error: DomainError) -> str:
    for kind in type(error).__mro__:
        if kind in _MESSAGES:
            return _MESSAGES[kind]
    return GENERIC
