"""Final clients (INT-03). They receive notices and never operate the system (RES-04)."""

from __future__ import annotations

from dataclasses import dataclass

from royexa.shared.errors import NotFound


class ClientNotFound(NotFound):
    pass


@dataclass(frozen=True)
class Client:
    id: str
    name: str
    route_id: str


class ClientCatalog:
    def __init__(self, clients: list[Client]) -> None:
        self._clients = {client.id: client for client in clients}

    def get(self, client_id: str) -> Client:
        try:
            return self._clients[client_id]
        except KeyError:
            raise ClientNotFound(client_id) from None
