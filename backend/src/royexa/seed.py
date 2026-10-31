"""Seeded demo data. Users and catalogs are a declared limitation (ALT-06B, RES-02)."""

from datetime import date

from royexa.adapters.memory import InMemoryStore, Tables
from royexa.cash_box.domain import CashBox
from royexa.clients.domain import Client, ClientCatalog
from royexa.identity_access.domain import Directory, Role, Route, User
from royexa.loans.domain import Installment, Loan
from royexa.shared.money import Money

ROUTE_ID = "ruta-1"
COLLECTOR_ID = "cobrador-1"
OPENING_CASH = Money(1_000_000_00)
COLLECTOR_LIMIT = Money(500_000_00)
ROUTE_LIMIT = Money(800_000_00)
FIXED_INTEREST_BPS = 2_000


def seed_directory() -> Directory:
    return Directory(
        users=[
            User(COLLECTOR_ID, "Cobrador uno", Role.COLLECTOR, COLLECTOR_LIMIT),
            User("cobrador-2", "Cobrador dos", Role.COLLECTOR, COLLECTOR_LIMIT),
            User("admin-1", "Administrador uno", Role.ADMIN),
            User("admin-2", "Administrador dos", Role.ADMIN),
        ],
        routes=[
            Route(ROUTE_ID, COLLECTOR_ID, ROUTE_LIMIT, FIXED_INTEREST_BPS),
            Route("ruta-2", "cobrador-2", ROUTE_LIMIT, FIXED_INTEREST_BPS),
        ],
    )


def seed_clients() -> ClientCatalog:
    return ClientCatalog(
        [
            Client("cliente-1", "Cliente sin prestamos", ROUTE_ID),
            Client("cliente-2", "Cliente con saldo pendiente", ROUTE_ID),
            Client("cliente-3", "Cliente con prestamo liquidado", ROUTE_ID),
            Client("cliente-4", "Cliente de otra ruta", "ruta-2"),
        ]
    )


def _prior_loan(loan_id: str, client_id: str, paid: Money) -> Loan:
    return Loan(
        loan_id,
        client_id,
        None,
        Money(100_000),
        Money(20_000),
        (Installment(1, date(2026, 9, 1), Money(120_000), paid),),
    )


def seed_store() -> InMemoryStore:
    unpaid = _prior_loan("prestamo-impago", "cliente-2", Money(50_000))
    settled = _prior_loan("prestamo-liquidado", "cliente-3", Money(120_000))
    boxes = [
        CashBox(f"caja-{collector}", collector, OPENING_CASH, OPENING_CASH)
        for collector in (COLLECTOR_ID, "cobrador-2")
    ]
    return InMemoryStore(
        Tables(
            loans={unpaid.id: unpaid, settled.id: settled},
            cash_boxes={box.id: box for box in boxes},
        )
    )
