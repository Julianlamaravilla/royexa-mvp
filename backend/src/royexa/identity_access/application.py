"""Login, sessions and logout (T6a, T6-P1). The tokens are opaque and random; the store
keeps their SHA-256 digest only."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from royexa.identity_access.domain import (
    Directory,
    InvalidCredentials,
    Session,
    SessionRequired,
    UnknownActor,
    User,
)
from royexa.identity_access.passwords import PasswordHasher
from royexa.identity_access.ports import AuthUnitOfWork
from royexa.shared.clock import Clock

INVALID_CREDENTIALS = "invalid credentials"  # never says which part was wrong
TOKEN_BYTES = 32  # 256 bits
DEFAULT_SESSION_TTL = timedelta(hours=12)


def digest_of(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class Login:
    token: str
    user: User
    expires_at: datetime


class Authenticator:
    def __init__(
        self,
        uow: Callable[[], AuthUnitOfWork],
        clock: Clock,
        directory: Directory,
        hasher: PasswordHasher,
        session_ttl: timedelta = DEFAULT_SESSION_TTL,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._directory = directory
        self._hasher = hasher
        self._ttl = session_ttl
        # An unknown user costs the same time as a wrong password.
        self._decoy = hasher.hash(secrets.token_urlsafe(16))

    def clock_now(self) -> datetime:
        return self._clock.now()

    def login(self, user_id: str, password: str) -> Login:
        with self._uow() as uow:
            credential = uow.auth.credential(user_id)
            stored = credential.password_hash if credential else self._decoy
            matches = self._hasher.verify(password, stored)
            try:
                user = self._directory.user(user_id)
            except UnknownActor:
                raise InvalidCredentials(INVALID_CREDENTIALS) from None
            if credential is None or not matches:
                raise InvalidCredentials(INVALID_CREDENTIALS)
            token = secrets.token_urlsafe(TOKEN_BYTES)
            now = self._clock.now()
            session = Session(digest_of(token), user.id, now, now + self._ttl)
            uow.auth.add_session(session)
            uow.commit()
        return Login(token, user, session.expires_at)

    def authenticate(self, token: str) -> User:
        session = self._valid_session(token)
        return self._directory.user(session.user_id)

    def logout(self, token: str) -> None:
        with self._uow() as uow:
            session = uow.auth.session(digest_of(token))
            if session is None or not session.is_valid(self._clock.now()):
                raise SessionRequired("no valid session")
            uow.auth.save_session(replace(session, revoked_at=self._clock.now()))
            uow.commit()

    def _valid_session(self, token: str) -> Session:
        with self._uow() as uow:
            session = uow.auth.session(digest_of(token))
        if session is None or not session.is_valid(self._clock.now()):
            raise SessionRequired("no valid session")
        return session
