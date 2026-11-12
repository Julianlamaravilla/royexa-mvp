"""Seeded users and routes. No account management: limitation declared by ALT-06B."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
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


class CurrentPasswordIncorrect(DomainError):
    """T6-P2: changing a password asks for the current one."""


class WeakPassword(DomainError):
    """T6-P2: at least twelve characters, and different from the current one."""


class DemoPasswordsInUse(DomainError):
    """T6-P2: the strict mode refuses to start while a demonstration password remains."""


class SessionRequired(DomainError):
    """There is no valid session: absent, unknown, expired or revoked (T6-P1)."""


MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION = timedelta(minutes=15)
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 256


@dataclass(frozen=True)
class Credential:
    """What proves a user is who they say: a salted hash, never the password (T6-P2), and
    the count of failed attempts in a row that can lock the user (T6-P3)."""

    user_id: str
    password_hash: str
    is_demo: bool = False
    """True while it is still the documented demonstration password."""
    failed_attempts: int = 0
    locked_until: datetime | None = None
    changed_at: datetime | None = None

    def is_locked(self, now: datetime) -> bool:
        return self.locked_until is not None and now < self.locked_until

    def after_failure(self, now: datetime) -> Credential:
        """Five failures in a row lock for fifteen minutes. Once a lock has run out, the
        count starts again from this failure."""
        expired = self.locked_until is not None and now >= self.locked_until
        attempts = (0 if expired else self.failed_attempts) + 1
        if attempts >= MAX_FAILED_ATTEMPTS:
            return replace(self, failed_attempts=0, locked_until=now + LOCK_DURATION)
        return replace(self, failed_attempts=attempts, locked_until=None if expired else self.locked_until)

    def after_success(self) -> Credential:
        return replace(self, failed_attempts=0, locked_until=None)

    def with_password(self, password_hash: str, now: datetime) -> Credential:
        return replace(
            self,
            password_hash=password_hash,
            is_demo=False,
            failed_attempts=0,
            locked_until=None,
            changed_at=now,
        )


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
