"""T1a: cash boxes, loans, renewal exceptions and notices persist in PostgreSQL.

Needs PostgreSQL: docker compose up -d --wait postgres, then uv run pytest -m postgres
"""

import os
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from database import reset_database
from support import FakeClock, Flow

from royexa.adapters.postgres_state import PostgresSession
from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.bootstrap import Settings, build_container
from royexa.cash_box.domain import CashBox
from royexa.loans.domain import Installment, Loan, RenewalException
from royexa.shared.errors import StaleWrite
from royexa.shared.money import Money
from royexa.shared.outbox import NoticeKind, NoticeStatus, OutboxMessage



pytestmark = pytest.mark.postgres

APP_URL = os.environ.get(
    "ROYEXA_LEDGER_URL", "postgresql://royexa_app:royexa_app@localhost:55432/royexa"
)
NOW = datetime(2026, 10, 30, 14, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def clean_database():
    reset_database()
    yield
    reset_database()


def _session() -> PostgresSession:
    return PostgresSession(APP_URL)


def _committed(write) -> None:
    session = _session()
    write(session)
    session.commit()


def _restarted_flow() -> Flow:
    """A new container over the same database, as after restarting the server."""
    built = build_container(Settings(ledger_url=APP_URL), FakeClock(), SimulatedNotifier())
    return Flow(TestClient(create_app(built)), built.notifier)


def test_t1a_seeded_state_is_in_the_database_and_seeding_twice_changes_nothing():
    build_container(Settings(ledger_url=APP_URL))
    build_container(Settings(ledger_url=APP_URL))

    session = _session()
    box = session.cash.open_box_of("cobrador-1")
    unpaid = session.loans.get("prestamo-impago")
    session.rollback()

    assert box.balance == Money(1_000_000_00)
    assert unpaid.outstanding == Money(70_000)


def test_t1a_cash_box_survives_a_restart_with_its_balance():
    build_container(Settings(ledger_url=APP_URL))

    def deduct(session: PostgresSession) -> None:
        box = session.cash.open_box_of("cobrador-1")
        box.deduct(Money(100_000))
        session.cash.save(box)

    _committed(deduct)

    session = _session()
    assert session.cash.open_box_of("cobrador-1").balance == Money(1_000_000_00 - 100_000)
    session.rollback()


def test_t1a_two_transactions_changing_the_same_box_do_not_overwrite_each_other():
    build_container(Settings(ledger_url=APP_URL))
    loser, winner = _session(), _session()
    box = loser.cash.open_box_of("cobrador-1")
    other = winner.cash.open_box_of("cobrador-1")
    other.deduct(Money(2))
    winner.cash.save(other)
    winner.commit()

    box.deduct(Money(1))
    with pytest.raises(StaleWrite):
        loser.cash.save(box)
    loser.rollback()

    session = _session()
    assert session.cash.open_box_of("cobrador-1").balance == Money(1_000_000_00 - 2)
    session.rollback()


def test_t1a_a_closed_box_is_no_longer_the_open_box_of_its_collector():
    build_container(Settings(ledger_url=APP_URL))
    box = CashBox("caja-nueva", "cobrador-9", Money(500), Money(500), closed=True)
    _committed(lambda session: session.cash.save(box))

    session = _session()
    assert session.cash.open_box_of("cobrador-9") is None
    session.rollback()


def test_t1a_loan_keeps_its_schedule_and_balance_across_sessions():
    loan = Loan(
        "prestamo-nuevo",
        "cliente-1",
        "desembolso-1",
        Money(100_000),
        Money(20_000),
        (
            Installment(1, date(2026, 11, 2), Money(60_000)),
            Installment(2, date(2026, 11, 3), Money(60_000), Money(10_000)),
        ),
    )
    _committed(lambda session: session.loans.add(loan))

    session = _session()
    assert session.loans.get("prestamo-nuevo") == loan
    assert session.loans.unsettled_for_client("cliente-1") == loan
    assert session.loans.get("no-existe") is None
    session.rollback()


def test_t1a_a_settled_loan_is_not_the_unsettled_loan_of_its_client():
    build_container(Settings(ledger_url=APP_URL))

    session = _session()
    assert session.loans.unsettled_for_client("cliente-3") is None
    assert session.loans.unsettled_for_client("cliente-2").id == "prestamo-impago"
    session.rollback()


def test_t1a_renewal_exception_is_stored_and_consumed_once():
    build_container(Settings(ledger_url=APP_URL))
    exception = RenewalException(
        "excepcion-1", "cliente-2", "prestamo-impago", "admin-1", "cliente recurrente", NOW
    )
    _committed(lambda session: session.loans.add_exception(exception))

    first = _session()
    assert first.loans.open_exception_for("cliente-2") == exception
    stored = first.loans.get_exception("excepcion-1")
    stored.consume("desembolso-7")
    first.loans.save_exception(stored)
    first.commit()

    second = _session()
    assert second.loans.open_exception_for("cliente-2") is None
    assert second.loans.get_exception("excepcion-1").consumed_by == "desembolso-7"
    second.rollback()


def test_t1a_notices_keep_their_order_status_and_payload():
    first = OutboxMessage.enqueue(NoticeKind.CONFIRMATION_CODE, "cliente-1", "d-1", NOW, {"code": "AB"})
    second = OutboxMessage.enqueue(NoticeKind.DISBURSEMENT_RECEIPT, "cliente-1", "d-2", NOW)

    def write(session: PostgresSession) -> None:
        session.outbox.add(first)
        session.outbox.add(second)

    _committed(write)

    reader = _session()
    assert [m.id for m in reader.outbox.pending()] == [first.id, second.id]
    assert [m.id for m in reader.outbox.all("d-2")] == [second.id]
    assert reader.outbox.get(first.id).payload == {"code": "AB"}
    delivered = reader.outbox.get(first.id)
    delivered.record_delivery(NOW)
    reader.outbox.save(delivered)
    reader.commit()

    after = _session()
    assert [m.id for m in after.outbox.pending()] == [second.id]
    sent = after.outbox.get(first.id)
    assert (sent.status, sent.attempts, sent.sent_at, sent.payload) == (
        NoticeStatus.SENT,
        1,
        NOW,
        {},
    )
    after.rollback()


def test_t1a_loan_cash_and_notices_of_a_confirmed_disbursement_survive_a_restart():
    built = build_container(Settings(ledger_url=APP_URL), FakeClock(), SimulatedNotifier())
    flow = Flow(TestClient(create_app(built)), built.notifier)
    opening = flow.cash_balance()
    disbursement = flow.approved()
    code = flow.issued_code(disbursement["id"])
    assert flow.confirm(disbursement["id"], code).status_code == 200

    restarted = _restarted_flow()

    assert restarted.cash_balance() == opening - disbursement["amount_cents"]
    assert [entry["entry_type"] for entry in restarted.ledger(disbursement["id"])] == ["DESEMBOLSO"]
    assert sorted(n["kind"] for n in restarted.notices(disbursement["id"])) == [
        "CODIGO_CONFIRMACION",
        "COMPROBANTE_DESEMBOLSO",
    ]
    # RN-05 reads the persisted loan: the client now owes a balance.
    assert restarted.request().status_code == 409
