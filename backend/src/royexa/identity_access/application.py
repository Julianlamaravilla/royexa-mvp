"""Login, sessions and logout (T6a, T6-P1). The tokens are opaque and random; the store
keeps their SHA-256 digest only."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from royexa.identity_access.domain import (
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    CurrentPasswordIncorrect,
    Directory,
    InvalidCredentials,
    Session,
    SessionRequired,
    UnknownActor,
    User,
    WeakPassword,
)
from royexa.identity_access.passwords import PasswordHasher
from royexa.identity_access.ports import AuthUnitOfWork
from royexa.shared.clock import Clock
from royexa.shared.errors import WriteConflict

INVALID_CREDENTIALS = "invalid credentials"  # never says which part was wrong
ATTEMPTS_ON_CONFLICT = 5  # a failure that races another one is counted again, never lost
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
        for attempt in range(1, ATTEMPTS_ON_CONFLICT + 1):
            try:
                return self._login_once(user_id, password)
            except WriteConflict:
                if attempt == ATTEMPTS_ON_CONFLICT:
                    raise
        raise AssertionError("unreachable")

    def _login_once(self, user_id: str, password: str) -> Login:
        with self._uow() as uow:
            credential = uow.auth.credential(user_id)
            now = self._clock.now()
            stored = credential.password_hash if credential else self._decoy
            matches = self._hasher.verify(password, stored)  # always runs: same time either way
            try:
                user = self._directory.user(user_id)
            except UnknownActor:
                raise InvalidCredentials(INVALID_CREDENTIALS) from None
            if credential is None or credential.is_locked(now):
                raise InvalidCredentials(INVALID_CREDENTIALS)
            if not matches:
                # T6-P3: the failure is kept even though the attempt is refused.
                uow.auth.save_credential(credential.after_failure(now))
                uow.commit()
                raise InvalidCredentials(INVALID_CREDENTIALS)
            if credential.failed_attempts or credential.locked_until:
                uow.auth.save_credential(credential.after_success())
            token = secrets.token_urlsafe(TOKEN_BYTES)
            session = Session(digest_of(token), user.id, now, now + self._ttl)
            uow.auth.add_session(session)
            uow.commit()
        return Login(token, user, session.expires_at)

    def change_password(self, token: str, current: str, new: str) -> None:
        """T6-P2. The current password is checked first and a wrong one counts toward the
        lock like a wrong login. A change ends the user's other sessions."""
        for attempt in range(1, ATTEMPTS_ON_CONFLICT + 1):
            try:
                return self._change_once(token, current, new)
            except WriteConflict:
                if attempt == ATTEMPTS_ON_CONFLICT:
                    raise
        raise AssertionError("unreachable")

    def _change_once(self, token: str, current: str, new: str) -> None:
        with self._uow() as uow:
            now = self._clock.now()
            session = uow.auth.session(digest_of(token))
            if session is None or not session.is_valid(now):
                raise SessionRequired("no valid session")
            credential = uow.auth.credential(session.user_id)
            if credential is None:
                raise SessionRequired("no credential")
            matches = self._hasher.verify(current, credential.password_hash)
            if credential.is_locked(now):
                raise CurrentPasswordIncorrect(INVALID_CREDENTIALS)
            if not matches:
                uow.auth.save_credential(credential.after_failure(now))
                uow.commit()
                raise CurrentPasswordIncorrect(INVALID_CREDENTIALS)
            if not MIN_PASSWORD_LENGTH <= len(new) <= MAX_PASSWORD_LENGTH:
                raise WeakPassword(
                    f"the new password has {MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters"
                )
            if new == current:
                raise WeakPassword("the new password differs from the current one")
            uow.auth.save_credential(credential.with_password(self._hasher.hash(new), now))
            for other in uow.auth.sessions_of(session.user_id):
                if other.token_hash != session.token_hash and other.is_valid(now):
                    uow.auth.save_session(replace(other, revoked_at=now))
            uow.commit()

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
