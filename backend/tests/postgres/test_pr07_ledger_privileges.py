"""PR-07, real privileges. RN-04, CA-08, EV-01, EV-02, ADR-001, ADR-004.

Needs PostgreSQL: docker compose up -d --wait postgres, then uv run pytest -m postgres
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import errors
from database import reset_database
from support import FakeClock, Flow

from royexa.adapters.memory import InMemoryUnitOfWork
from royexa.adapters.postgres_ledger import PostgresLedgerRepository, PostgresLedgerSession
from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.bootstrap import Settings, build_container
from royexa.cash_box.domain import CashBox
from royexa.ledger.domain import DuplicateLedgerEntry, LedgerEntry, LedgerEntryType
from royexa.migrate import MIGRATOR_URL, apply_migrations
from royexa.seed import COLLECTOR_ID, seed_store
from royexa.shared.errors import StaleWrite
from royexa.shared.money import Money

pytestmark = pytest.mark.postgres

APP_URL = os.environ.get(
    "ROYEXA_LEDGER_URL", "postgresql://royexa_app:royexa_app@localhost:55432/royexa"
)
FORBIDDEN = {
    "UPDATE": "UPDATE ledger_entry SET amount_cents = 1 WHERE id = %s",
    "DELETE": "DELETE FROM ledger_entry WHERE id = %s",
    "TRUNCATE": "TRUNCATE ledger_entry",
}
ALL_MIGRATIONS = [
    "001_ledger.sql",
    "002_state.sql",
    "003_disbursements.sql",
    "004_clients.sql",
    "005_loan_order.sql",
    "006_payments.sql",
    "007_non_payments.sql",
    "008_payment_receipt.sql",
    "009_daily_box.sql",
    "010_cash_close.sql",
    "011_adjustments.sql",
]
NOW = datetime(2026, 10, 30, 14, 0, tzinfo=UTC)
RECEIPT = "COMPROBANTE_DESEMBOLSO"
CONNECTION_DRAIN_SECONDS = 3


def _entry(disbursement_id: str) -> LedgerEntry:
    return LedgerEntry(
        str(uuid4()),
        disbursement_id,
        LedgerEntryType.DISBURSEMENT,
        Money(100_000),
        "caja-cobrador-1",
        "cobrador-1",
        NOW,
        NOW,
    )


@pytest.fixture(scope="module", autouse=True)
def schema():
    apply_migrations()


@pytest.fixture
def entry():
    """A committed row, removed afterwards by the owner, which the app role cannot do."""
    created = _entry(str(uuid4()))
    session = PostgresLedgerSession(APP_URL)
    session.repository.append(created)
    session.commit()
    yield created
    with psycopg.connect(MIGRATOR_URL) as owner:
        owner.execute("DELETE FROM ledger_entry WHERE id = %s", (created.id,))


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def container(clock):
    reset_database()
    yield build_container(Settings(ledger_url=APP_URL), clock, SimulatedNotifier())
    reset_database()


@pytest.fixture
def flow(container) -> Flow:
    return Flow(TestClient(create_app(container)), container.notifier)


def _session() -> PostgresLedgerSession:
    return PostgresLedgerSession(APP_URL)


def _stored(disbursement_id: str) -> list[LedgerEntry]:
    with psycopg.connect(APP_URL) as connection:
        return PostgresLedgerRepository(connection).for_disbursement(disbursement_id)


def _app_connections() -> int:
    with psycopg.connect(MIGRATOR_URL) as owner:
        return owner.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE usename = 'royexa_app'"
        ).fetchone()[0]


def _assert_no_app_connection_stays_open() -> None:
    """A closed backend leaves pg_stat_activity shortly after, not at once."""
    deadline = time.monotonic() + CONNECTION_DRAIN_SECONDS
    while _app_connections() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert _app_connections() == 0


def _kill_app_connections() -> None:
    with psycopg.connect(MIGRATOR_URL) as owner:
        owner.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = 'royexa_app'"
        )


def _privileges() -> dict[str, bool]:
    with psycopg.connect(MIGRATOR_URL) as connection:
        return {
            privilege: connection.execute(
                "SELECT has_table_privilege('royexa_app', 'ledger_entry', %s)", (privilege,)
            ).fetchone()[0]
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE")
        }


APPEND_ONLY = {
    "SELECT": True,
    "INSERT": True,
    "UPDATE": False,
    "DELETE": False,
    "TRUNCATE": False,
}


@pytest.mark.parametrize("operation", FORBIDDEN)
def test_pr07_app_role_cannot_change_a_committed_entry(entry, operation):
    """PR-07 / EV-01 / RN-04 / CA-08: each attempt fails on permission; the row stays."""
    statement = FORBIDDEN[operation]
    params = () if operation == "TRUNCATE" else (entry.id,)
    with psycopg.connect(APP_URL) as connection:
        with pytest.raises(errors.InsufficientPrivilege):
            connection.execute(statement, params)

    assert _stored(entry.disbursement_id) == [entry]


def test_pr07_catalog_grants_only_select_and_insert():
    """PR-07 / EV-02 / ADR-001: the catalog shows no change privilege after migrating."""
    assert _privileges() == APPEND_ONLY


def test_pr07_catalog_lists_no_other_grant_on_any_table():
    """PR-07 / EV-02 / RA-01: exact grants on every table, also through PUBLIC. A new table
    the role can reach, such as a change log, fails here until it is decided on."""
    with psycopg.connect(MIGRATOR_URL) as connection:
        grants = connection.execute(
            """
            SELECT table_name, grantee, privilege_type
            FROM information_schema.role_table_grants
            WHERE table_schema = 'public' AND grantee IN ('royexa_app', 'PUBLIC')
            """
        ).fetchall()

    # T1a decided: mutable state may be inserted and updated, never deleted.
    state = ("cash_box", "loan", "loan_installment", "outbox_message", "renewal_exception")
    assert sorted(grants) == sorted(
        [
            ("ledger_entry", "royexa_app", "INSERT"),
            ("ledger_entry", "royexa_app", "SELECT"),
        ]
        + [
            (table, "royexa_app", privilege)
            for table in state
            for privilege in ("INSERT", "SELECT", "UPDATE")
        ]
        # T1b: disbursements may change state; refused attempts are append-only (RN-06).
        + [("disbursement", "royexa_app", privilege) for privilege in ("INSERT", "SELECT", "UPDATE")]
        + [("refused_approval_attempt", "royexa_app", p) for p in ("INSERT", "SELECT")]
        # T2a: clients are registered and read, never changed or deleted by the application.
        + [("client", "royexa_app", p) for p in ("INSERT", "SELECT")]
        # T3a: payments and their allocation are append-only (RF-01).
        + [(t, "royexa_app", p) for t in ("payment", "payment_allocation") for p in ("INSERT", "SELECT")]
        # T3b: a non-payment is a visit that happened and is never edited.
        + [("non_payment", "royexa_app", p) for p in ("INSERT", "SELECT")]
        # T5b: a close is append-only (RN-02, RF-02).
        + [("cash_close", "royexa_app", p) for p in ("INSERT", "SELECT")]
    )


def test_pr07_catalog_shows_no_column_level_change_privilege():
    """PR-07 / EV-02: a grant on one column would escape the table-level check."""
    with psycopg.connect(MIGRATOR_URL) as connection:
        grants = connection.execute(
            """
            SELECT column_name, privilege_type
            FROM information_schema.column_privileges
            WHERE table_schema = 'public' AND table_name = 'ledger_entry'
              AND grantee IN ('royexa_app', 'PUBLIC')
              AND privilege_type NOT IN ('SELECT', 'INSERT')
            """
        ).fetchall()

    assert grants == []


def test_pr07_app_role_has_no_way_around_the_grants():
    """PR-07 / EV-02 / ADR-001: owning the table or bypassing checks would void them."""
    with psycopg.connect(MIGRATOR_URL) as connection:
        role = connection.execute(
            "SELECT rolsuper, rolbypassrls, rolcreaterole, rolcreatedb FROM pg_roles "
            "WHERE rolname = 'royexa_app'"
        ).fetchone()
        owner = connection.execute(
            "SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid = 'ledger_entry'::regclass"
        ).fetchone()[0]
        member_of = connection.execute(
            "SELECT count(*) FROM pg_auth_members m JOIN pg_roles r ON r.oid = m.member "
            "WHERE r.rolname = 'royexa_app'"
        ).fetchone()[0]

    assert role == (False, False, False, False)
    assert owner == "royexa_migrator"
    assert member_of == 0


def test_pr07_migrations_are_repeatable():
    """PR-07 / EV-02: applying twice leaves the same privileges and raises nothing."""
    assert apply_migrations() == ALL_MIGRATIONS
    assert apply_migrations() == ALL_MIGRATIONS
    assert _privileges() == APPEND_ONLY


def test_pr07_constraint_refuses_a_second_entry_of_the_same_type(entry):
    """PR-07 / EV-12 / ADR-004: the database holds the guarantee, not only the code."""
    with psycopg.connect(APP_URL) as connection:
        with pytest.raises(DuplicateLedgerEntry):
            PostgresLedgerRepository(connection).append(_entry(entry.disbursement_id))


def test_pr07_disbursement_flow_writes_one_entry_on_the_real_ledger(flow):
    """PR-07 / CA-05 / EV-12: the full flow through the Postgres adapter settles once."""
    disbursement = flow.approved()
    code = flow.issued_code(disbursement["id"])

    assert flow.confirm(disbursement["id"], code).status_code == 200
    assert flow.confirm(disbursement["id"], code).status_code == 200

    assert [item["entry_type"] for item in flow.ledger(disbursement["id"])] == ["DESEMBOLSO"]


def test_pr07_expired_attempt_keeps_its_reason_on_the_real_ledger(flow, clock):
    """PR-07 / CA-06 / RN-03: the entry with its reason satisfies the real constraints."""
    opening_balance = flow.cash_balance()
    disbursement = flow.approved()
    code = flow.issued_code(disbursement["id"])
    clock.advance(timedelta(hours=2))

    assert flow.confirm(disbursement["id"], code).status_code == 409

    [entry] = flow.ledger(disbursement["id"])
    assert (entry["entry_type"], entry["reason"]) == ("DESEMBOLSO_CADUCADO", "codigo_caducado")
    assert flow.cash_balance() == opening_balance


def test_pr07_two_simultaneous_confirmations_settle_once_on_the_real_ledger(flow):
    """PR-07 / EV-12 / ADR-004: the loser blocks on the real constraint, then replays."""
    opening_balance = flow.cash_balance()
    disbursement = flow.approved()
    code = flow.issued_code(disbursement["id"])
    start = Barrier(2)

    def confirm(_: int):
        start.wait()
        return flow.confirm(disbursement["id"], code)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(confirm, range(2)))

    assert [response.status_code for response in responses] == [200, 200]
    assert len(flow.ledger(disbursement["id"])) == 1
    assert flow.cash_balance() == opening_balance - disbursement["amount_cents"]
    assert [n["kind"] for n in flow.notices(disbursement["id"])].count(RECEIPT) == 1


BOX_DAY = date(2026, 10, 30)


def _store_with_open_box():
    """An in-memory store holding the box of the day, as its first movement would open it."""
    store = seed_store()
    box = CashBox.open(COLLECTOR_ID, BOX_DAY, Money(1_000_000_00))
    store.tables.cash_boxes[box.id] = box
    return store


def test_pr07_stale_commit_leaves_no_entry_on_the_real_ledger():
    """PR-07 / ADR-002: entry and deduction commit together, so losing drops the entry."""
    store = _store_with_open_box()
    lost = _entry(str(uuid4()))

    with pytest.raises(StaleWrite):
        with InMemoryUnitOfWork(store, _session) as loser:
            box = loser.cash.box_of_day(COLLECTOR_ID, BOX_DAY)
            box.deduct(Money(1))
            loser.cash.save(box)
            loser.ledger.append(lost)
            with InMemoryUnitOfWork(store, _session) as winner:
                other = winner.cash.box_of_day(COLLECTOR_ID, BOX_DAY)
                other.deduct(Money(2))
                winner.cash.save(other)
                winner.commit()
            loser.commit()

    assert _stored(lost.disbursement_id) == []
    _assert_no_app_connection_stays_open()


def test_pr07_failed_ledger_commit_changes_nothing_and_surfaces_its_error():
    """PR-07 / ADR-002: if the database goes, neither side commits."""
    store = _store_with_open_box()
    opening = store.tables.cash_boxes.copy()
    lost = _entry(str(uuid4()))

    with pytest.raises(psycopg.OperationalError):
        with InMemoryUnitOfWork(store, _session) as uow:
            box = uow.cash.box_of_day(COLLECTOR_ID, BOX_DAY)
            box.deduct(Money(1))
            uow.cash.save(box)
            uow.ledger.append(lost)
            _kill_app_connections()
            uow.commit()

    assert store.tables.cash_boxes == opening
    assert _stored(lost.disbursement_id) == []
    _assert_no_app_connection_stays_open()


def test_pr07_session_closes_once_when_its_commit_fails():
    """PR-07: the rollback that follows a failed commit must not raise over its error."""
    session = PostgresLedgerSession(APP_URL)
    session.repository.append(_entry(str(uuid4())))
    _kill_app_connections()

    with pytest.raises(psycopg.OperationalError):
        session.commit()
    session.rollback()

    _assert_no_app_connection_stays_open()


def test_pr07_session_rollback_after_commit_is_harmless():
    """PR-07: the unit of work can always clean up, whatever already ended the session."""
    session = PostgresLedgerSession(APP_URL)
    session.commit()

    session.rollback()
    session.rollback()

    _assert_no_app_connection_stays_open()


def test_pr07_unit_of_work_reused_after_commit_still_releases_its_connection():
    """PR-07: `_committed` belongs to one block, not to the object."""
    uow = InMemoryUnitOfWork(seed_store(), _session)
    with uow:
        uow.commit()

    with uow:
        uow.ledger.all()

    _assert_no_app_connection_stays_open()


def test_pr07_every_path_of_the_flow_returns_its_connection(flow, clock):
    """PR-07: read-only, replay, refusal and commit all end with nothing left open."""
    settled = flow.approved()
    code = flow.issued_code(settled["id"])
    assert flow.confirm(settled["id"], code).status_code == 200
    assert flow.confirm(settled["id"], code).status_code == 200
    flow.read(settled["id"])
    flow.ledger()
    flow.notices()

    refused = flow.requested(actor="admin-1", client="cliente-3")
    assert flow.approve(refused["id"], actor="admin-1").status_code >= 400
    assert flow.confirm("no-existe", "CODIGO").status_code == 404

    _assert_no_app_connection_stays_open()
