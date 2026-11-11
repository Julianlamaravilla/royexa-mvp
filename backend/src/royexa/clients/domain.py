"""Final clients (INT-03). They receive notices and never operate the system (RES-04).
RF-05: the administrator registers them on a route."""

from __future__ import annotations

from dataclasses import dataclass

from royexa.identity_access.domain import Route, User
from royexa.shared.errors import DomainError, NotFound
from royexa.shared.ids import new_id


class ClientNotFound(NotFound):
    pass


class InvalidClient(DomainError):
    pass


class ClientRegistrationNotAllowed(DomainError):
    """RF-05: only an administrator registers clients."""


@dataclass(frozen=True)
class Client:
    id: str
    name: str
    route_id: str

    @classmethod
    def register(cls, actor: User, name: str, route: Route) -> Client:
        if not actor.is_admin:
            raise ClientRegistrationNotAllowed(actor.id)
        if not name.strip():
            raise InvalidClient("the client needs a name")
        return cls(new_id(), name.strip(), route.id)
