from __future__ import annotations

from typing import Protocol, Self

from royexa.clients.domain import Client


class ClientRepository(Protocol):
    def add(self, client: Client) -> None: ...
    def get(self, client_id: str) -> Client | None: ...
    def all(self) -> list[Client]:
        """In order of registration."""
        ...


class ClientsUnitOfWork(Protocol):
    clients: ClientRepository

    def __enter__(self) -> Self: ...
    def __exit__(self, *exc_info: object) -> None: ...
    def commit(self) -> None: ...
