"""Seeded users and routes. No account management: limitation declared by ALT-06B."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from royexa.shared.errors import DomainError, NotFound
from royexa.shared.money import Money


class Role(StrEnum):
    COLLECTOR = "COBRADOR"
    ADMIN = "ADMINISTRADOR"


class UnknownActor(NotFound):
    pass


class RouteNotFound(NotFound):
    pass


class InvalidCredentials(DomainError):
    """T6-P3: the same answer for an unknown user and for a wrong password."""


class SessionRequired(DomainError):
    """There is no valid session: absent, unknown, expired or revoked (T6-P1)."""


@dataclass(frozen=True)
class Credential:
    """What proves a user is who they say: a salted hash, never the password (T6-P2)."""

    user_id: str
    password_hash: str
    is_demo: bool = False
    """True while it is still the documented demonstration password."""


@dataclass(frozen=True)
class Session:
    """T6-P1: only a digest of the token is kept, so a copy of the database cannot be used
    to act as anyone."""

    token_hash: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None

    def is_valid(self, now: datetime) -> bool:
        return self.revoked_at is None and now < self.expires_at


@dataclass(frozen=True)
class User:
    id: str
    name: str
    role: Role
    disbursement_limit: Money | None = None
    opening_cash: Money | None = None
    """The collector's fixed float: the opening balance of each day's cash box (T5-P2)."""

    @property
    def is_admin(self) -> bool:
        return self.role is Role.ADMIN


@dataclass(frozen=True)
class Route:
    id: str
    collector_id: str
    max_disbursement: Money
    interest_bps: int


class Directory:
    def __init__(self, users: list[User], routes: list[Route]) -> None:
        self._users = {user.id: user for user in users}
        self._routes = {route.id: route for route in routes}

    def user(self, user_id: str) -> User:
        try:
            return self._users[user_id]
        except KeyError:
            raise UnknownActor(user_id) from None

    def users(self) -> list[User]:
        return list(self._users.values())

    def opening_cash(self, collector_id: str) -> Money | None:
        return self.user(collector_id).opening_cash

    def route_of_collector(self, collector_id: str) -> Route:
        for route in self._routes.values():
            if route.collector_id == collector_id:
                return route
        raise RouteNotFound(collector_id)

    def route(self, route_id: str) -> Route:
        try:
            return self._routes[route_id]
        except KeyError:
            raise RouteNotFound(route_id) from None
