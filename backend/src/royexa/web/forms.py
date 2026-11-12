"""One-time form tokens (T7-P4). Each form carries a token tied to the session that asked
for it. The server accepts it once; a repeat gets the result already recorded and never
repeats the effect. It also stops a form posted from another site, which cannot know it."""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum, auto
from typing import Protocol, Self

from royexa.identity_access.application import digest_of
from royexa.identity_access.ports import AuthRepository
from royexa.shared.clock import Clock
from royexa.shared.errors import WriteConflict

TOKEN_BYTES = 32
CLAIM_ATTEMPTS = 5


@dataclass(frozen=True)
class Outcome:
    """What a form did: shown on the result page, also to a repeat of the same form."""

    kind: str  # "ok" or "error"
    text: str
    next_path: str


@dataclass(frozen=True)
class FormToken:
    token_hash: str
    session_hash: str
    purpose: str
    created_at: datetime
    used_at: datetime | None = None
    outcome: Outcome | None = None


class FormTokenRepository(Protocol):
    def add(self, token: FormToken) -> None: ...
    def get(self, token_hash: str) -> FormToken | None: ...
    def save(self, token: FormToken) -> None: ...


class FormTokensUnitOfWork(Protocol):
    form_tokens: FormTokenRepository
    auth: AuthRepository

    def __enter__(self) -> Self: ...
    def __exit__(self, *exc_info: object) -> None: ...
    def commit(self) -> None: ...


class ClaimState(Enum):
    FRESH = auto()  # first time: do the work
    REPLAY = auto()  # done before: show the recorded result
    PENDING = auto()  # being done right now by another request
    INVALID = auto()  # unknown, other session, other purpose, or dead session


@dataclass(frozen=True)
class Claim:
    state: ClaimState
    outcome: Outcome | None = None


class FormTokens:
    def __init__(self, uow: Callable[[], FormTokensUnitOfWork], clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def issue(self, session_token: str, purpose: str) -> str:
        token = secrets.token_urlsafe(TOKEN_BYTES)
        with self._uow() as uow:
            uow.form_tokens.add(
                FormToken(digest_of(token), digest_of(session_token), purpose, self._clock.now())
            )
            uow.commit()
        return token

    def claim(self, token: str, session_token: str, purpose: str) -> Claim:
        """Of several simultaneous claims exactly one is fresh; the others lose the write and
        are told it is being done or what it did."""
        for attempt in range(1, CLAIM_ATTEMPTS + 1):
            try:
                return self._claim_once(token, session_token, purpose)
            except WriteConflict:
                if attempt == CLAIM_ATTEMPTS:
                    raise
        raise AssertionError("unreachable")

    def _claim_once(self, token: str, session_token: str, purpose: str) -> Claim:
        with self._uow() as uow:
            now = self._clock.now()
            session = uow.auth.session(digest_of(session_token))
            row = uow.form_tokens.get(digest_of(token)) if token else None
            if (
                session is None
                or not session.is_valid(now)
                or row is None
                or row.session_hash != session.token_hash
                or row.purpose != purpose
            ):
                return Claim(ClaimState.INVALID)
            if row.used_at is None:
                uow.form_tokens.save(replace(row, used_at=now))
                uow.commit()
                return Claim(ClaimState.FRESH)
            if row.outcome is None:
                return Claim(ClaimState.PENDING)
            return Claim(ClaimState.REPLAY, row.outcome)

    def finish(self, token: str, outcome: Outcome) -> None:
        with self._uow() as uow:
            row = uow.form_tokens.get(digest_of(token))
            if row is not None:
                uow.form_tokens.save(replace(row, outcome=outcome))
                uow.commit()

    def outcome_of(self, token: str, session_token: str) -> Outcome | None:
        with self._uow() as uow:
            row = uow.form_tokens.get(digest_of(token)) if token else None
            if row is None or row.session_hash != digest_of(session_token):
                return None
            return row.outcome
