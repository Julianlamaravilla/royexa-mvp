"""Outbox port (ADR-002). A message is the "Aviso": business modules enqueue it in
their own transaction and never touch notifications (EV-09)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from royexa.shared.ids import new_id

MAX_DELIVERY_ATTEMPTS = 5


class NoticeKind(StrEnum):
    CONFIRMATION_CODE = "CODIGO_CONFIRMACION"
    DISBURSEMENT_RECEIPT = "COMPROBANTE_DESEMBOLSO"


class NoticeStatus(StrEnum):
    PENDING = "PENDIENTE"
    SENT = "ENVIADO"
    FAILED = "FALLIDO"


@dataclass
class OutboxMessage:
    id: str
    kind: NoticeKind
    client_id: str
    disbursement_id: str
    created_at: datetime
    payload: dict[str, str] = field(default_factory=dict)
    status: NoticeStatus = NoticeStatus.PENDING
    attempts: int = 0
    last_error: str | None = None
    sent_at: datetime | None = None

    @classmethod
    def enqueue(
        cls,
        kind: NoticeKind,
        client_id: str,
        disbursement_id: str,
        created_at: datetime,
        payload: dict[str, str] | None = None,
    ) -> OutboxMessage:
        return cls(new_id(), kind, client_id, disbursement_id, created_at, payload or {})

    def record_delivery(self, at: datetime) -> None:
        self.attempts += 1
        self.status = NoticeStatus.SENT
        self.sent_at = at
        self.last_error = None
        self.payload = {}

    def record_failure(self, error: str) -> None:
        """EV-03: each dispatch counts one attempt; the fifth marks it failed (CA-12)."""
        self.attempts += 1
        self.last_error = error
        if self.attempts >= MAX_DELIVERY_ATTEMPTS:
            self.status = NoticeStatus.FAILED
            self.payload = {}


class Outbox(Protocol):
    def add(self, message: OutboxMessage) -> None: ...
    def get(self, message_id: str) -> OutboxMessage | None: ...
    def save(self, message: OutboxMessage) -> None: ...
    def pending(self) -> list[OutboxMessage]: ...
    def all(self, disbursement_id: str | None = None) -> list[OutboxMessage]: ...
