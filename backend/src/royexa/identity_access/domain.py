"""Seeded users and routes. No account management: limitation declared by ALT-06B."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from royexa.shared.errors import NotFound
from royexa.shared.money import Money


class Role(StrEnum):
    COLLECTOR = "COBRADOR"
    ADMIN = "ADMINISTRADOR"


class UnknownActor(NotFound):
    pass


class RouteNotFound(NotFound):
    pass


@dataclass(frozen=True)
class User:
    id: str
    name: str
    role: Role
    disbursement_limit: Money | None = None

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

    def route(self, route_id: str) -> Route:
        try:
            return self._routes[route_id]
        except KeyError:
            raise RouteNotFound(route_id) from None
