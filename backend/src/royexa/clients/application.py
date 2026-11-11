"""Client use cases (RF-05). They coordinate; the aggregate decides."""

from __future__ import annotations

from collections.abc import Callable

from royexa.clients.domain import Client, ClientNotFound
from royexa.clients.ports import ClientsUnitOfWork
from royexa.identity_access.domain import Directory, User


class RegisterClient:
    def __init__(self, uow: Callable[[], ClientsUnitOfWork], directory: Directory) -> None:
        self._uow = uow
        self._directory = directory

    def execute(self, actor: User, name: str, route_id: str) -> Client:
        route = self._directory.route(route_id)
        client = Client.register(actor, name, route)
        with self._uow() as uow:
            uow.clients.add(client)
            uow.commit()
        return client


class ClientQueries:
    def __init__(self, uow: Callable[[], ClientsUnitOfWork]) -> None:
        self._uow = uow

    def get(self, client_id: str) -> Client:
        with self._uow() as uow:
            client = uow.clients.get(client_id)
        if client is None:
            raise ClientNotFound(client_id)
        return client

    def all(self) -> list[Client]:
        with self._uow() as uow:
            return uow.clients.all()
