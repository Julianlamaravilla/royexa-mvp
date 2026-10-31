"""Invocable outbox dispatcher (ADR-002). Sole reader of events; no background worker."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock

from royexa.notifications.ports import (
    Notification,
    NotificationsUnitOfWork,
    Notifier,
    NotifierUnavailable,
)
from royexa.shared.clock import Clock
from royexa.shared.outbox import NoticeStatus, OutboxMessage


@dataclass(frozen=True)
class DispatchReport:
    attempted: int
    sent: int


class NotificationDispatcher:
    def __init__(
        self,
        uow: Callable[[], NotificationsUnitOfWork],
        notifier: Notifier,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._notifier = notifier
        self._clock = clock
        self._lock = Lock()

    def dispatch(self) -> DispatchReport:
        with self._lock:
            with self._uow() as uow:
                pending = [message.id for message in uow.outbox.pending()]
            outcomes = [self._deliver(message_id) for message_id in pending]
        return DispatchReport(attempted=len(outcomes), sent=outcomes.count(NoticeStatus.SENT))

    def _deliver(self, message_id: str) -> NoticeStatus:
        with self._uow() as uow:
            message = uow.outbox.get(message_id)
            try:
                self._notifier.send(self._notification(message))
            except NotifierUnavailable as error:
                message.record_failure(str(error))
            else:
                message.record_delivery(self._clock.now())
            uow.outbox.save(message)
            uow.commit()
            return message.status

    @staticmethod
    def _notification(message: OutboxMessage) -> Notification:
        return Notification(
            message.id,
            message.client_id,
            message.disbursement_id,
            message.kind,
            dict(message.payload),
        )


class NoticeQueries:
    """CA-12: what the administrator reads to learn a client was not notified."""

    def __init__(self, uow: Callable[[], NotificationsUnitOfWork]) -> None:
        self._uow = uow

    def list(self, disbursement_id: str | None = None) -> list[OutboxMessage]:
        with self._uow() as uow:
            return uow.outbox.all(disbursement_id)
