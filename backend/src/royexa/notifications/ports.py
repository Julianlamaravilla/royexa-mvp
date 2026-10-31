"""Notifier port (RES-03, RES-05): the real provider stays behind this contract (EXT-05)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Self

from royexa.shared.outbox import NoticeKind, Outbox


class NotifierUnavailable(Exception):
    """The channel did not confirm the delivery (CA-12)."""


@dataclass(frozen=True)
class Notification:
    message_id: str
    client_id: str
    disbursement_id: str
    kind: NoticeKind
    payload: dict[str, str] = field(default_factory=dict)


class Notifier(Protocol):
    def send(self, notification: Notification) -> None: ...


class NotificationsUnitOfWork(Protocol):
    outbox: Outbox

    def __enter__(self) -> Self: ...
    def __exit__(self, *exc_info: object) -> None: ...
    def commit(self) -> None: ...
