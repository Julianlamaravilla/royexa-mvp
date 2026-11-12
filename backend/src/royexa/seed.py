"""Seeded demo data. Users and catalogs are a declared limitation (ALT-06B, RES-02)."""

import json
from datetime import date
from functools import lru_cache
from pathlib import Path

from royexa.adapters.memory import InMemoryStore, Tables
from royexa.clients.domain import Client
from royexa.identity_access.domain import Credential, Directory, Role, Route, User
from royexa.identity_access.passwords import PasswordHasher
from royexa.loans.domain import Installment, Loan
from royexa.shared.money import Money

PILOT_DIRECTORY = Path(__file__).resolve().parents[2] / "pilot" / "directory.json"
ROUTE_ID = "ruta-1"
COLLECTOR_ID = "cobrador-1"
OPENING_CASH = Money(1_000_000_00)
COLLECTOR_LIMIT = Money(500_000_00)
ROUTE_LIMIT = Money(800_000_00)
FIXED_INTEREST_BPS = 2_000


def seed_directory() -> Directory:
    return Directory(
        users=[
            User(COLLECTOR_ID, "Cobrador uno", Role.COLLECTOR, COLLECTOR_LIMIT, OPENING_CASH),
            User("cobrador-2", "Cobrador dos", Role.COLLECTOR, COLLECTOR_LIMIT, OPENING_CASH),
            User("admin-1", "Administrador uno", Role.ADMIN),
            User("admin-2", "Administrador dos", Role.ADMIN),
        ],
        routes=[
            Route(ROUTE_ID, COLLECTOR_ID, ROUTE_LIMIT, FIXED_INTEREST_BPS),
            Route("ruta-2", "cobrador-2", ROUTE_LIMIT, FIXED_INTEREST_BPS),
        ],
    )


def load_directory(path: Path) -> Directory:
    """T10-P5: the users and routes of the pilot, read from a file (amounts in cents). A mistake
    stops the start with a message that names it, rather than failing on the first request."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"the directory file does not exist: {path}") from None
    except json.JSONDecodeError as error:
        raise ValueError(f"the directory file is not valid JSON: {error}") from None
    users, routes = [], []
    for item in data.get("users", []):
        try:
            role = Role(item["role"])
        except (KeyError, ValueError):
            raise ValueError(f"user {item.get('id')!r} has an unknown role: {item.get('role')!r}") from None
        limit, cash = item.get("disbursement_limit_cents"), item.get("opening_cash_cents")
        if role is Role.COLLECTOR and (limit is None or cash is None):
            raise ValueError(f"collector {item['id']!r} needs a disbursement limit and an opening cash")
        users.append(
            User(item["id"], item["name"], role, Money(limit) if limit is not None else None,
                 Money(cash) if cash is not None else None)
        )
    for item in data.get("routes", []):
        routes.append(
            Route(item["id"], item["collector_id"], Money(item["max_disbursement_cents"]), item["interest_bps"])
        )
    served = {route.collector_id for route in routes}
    for user in users:
        if user.role is Role.COLLECTOR and user.id not in served:
            raise ValueError(f"collector {user.id!r} has no route")
    for route in routes:
        if route.collector_id not in {u.id for u in users if u.role is Role.COLLECTOR}:
            raise ValueError(f"route {route.id!r} names an unknown collector: {route.collector_id!r}")
    return Directory(users, routes)


def directory_for(seed: str, path: Path | None = None) -> Directory:
    return load_directory(path or PILOT_DIRECTORY) if seed == "pilot" else seed_directory()


def demo_password(user_id: str) -> str:
    """T6-P2: the documented demonstration password of a seeded user. Valid only for local
    development and tests, like the other credentials of the demonstration; T6b lets a
    server refuse to start while any user still has it."""
    return f"demo-{user_id}-royexa"


@lru_cache(maxsize=4)
def _seed_credentials(hasher: PasswordHasher) -> tuple[Credential, ...]:
    return tuple(
        Credential(user.id, hasher.hash(demo_password(user.id)), is_demo=True)
        for user in seed_directory().users()
    )


def seed_credentials(hasher: PasswordHasher) -> list[Credential]:
    return list(_seed_credentials(hasher))


def seed_clients() -> list[Client]:
    return [
        Client("cliente-1", "Cliente sin prestamos", ROUTE_ID),
        Client("cliente-2", "Cliente con saldo pendiente", ROUTE_ID),
        Client("cliente-3", "Cliente con prestamo liquidado", ROUTE_ID),
        Client("cliente-4", "Cliente de otra ruta", "ruta-2"),
    ]


def _prior_loan(loan_id: str, client_id: str, paid: Money) -> Loan:
    return Loan(
        loan_id,
        client_id,
        None,
        Money(100_000),
        Money(20_000),
        (Installment(1, date(2026, 9, 1), Money(120_000), paid),),
    )


def seed_loans() -> list[Loan]:
    return [
        _prior_loan("prestamo-impago", "cliente-2", Money(50_000)),
        _prior_loan("prestamo-liquidado", "cliente-3", Money(120_000)),
    ]


def seed_store(hasher: PasswordHasher | None = None) -> InMemoryStore:
    hasher = hasher or PasswordHasher()
    return InMemoryStore(
        Tables(
            credentials={c.user_id: c for c in seed_credentials(hasher)},
            clients={client.id: client for client in seed_clients()},
            loans={loan.id: loan for loan in seed_loans()},
        )
    )
