"""T1b: disbursements persist in PostgreSQL, with their refused approval attempts.

Needs PostgreSQL: docker compose up -d --wait postgres, then uv run pytest -m postgres
"""

import os
from datetime import UTC, datetime, timedelta

import pytest
from database import reset_database
from fastapi.testclient import TestClient
from support import FakeClock, Flow

from royexa.adapters.postgres_state import PostgresSession
from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.api import create_app
from royexa.bootstrap import Settings, build_container
from royexa.identity_access.domain import Role
from royexa.loans.domain import LoanTerms
from royexa.sales.domain import (
    ConfirmationCode,
    Disbursement,
    DisbursementStatus,
    RefusedApprovalAttempt,
)
from royexa.shared.errors import StaleWrite
from royexa.shared.money import Money

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


def _disbursement(disbursement_id: str = "d-1") -> Disbursement:
    return Disbursement(
        id=disbursement_id,
        client_id="cliente-1",
        route_id="ruta-1",
        collector_id="cobrador-1",
        requested_by="cobrador-1",
        requested_at=NOW,
        terms=LoanTerms(Money(100_000), 20, 20),
        interest=Money(20_000),
        status=DisbursementStatus.REQUESTED,
    )


def _session() -> PostgresSession:
    return PostgresSession(APP_URL)


def _committed(write) -> None:
    session = _session()
    write(session)
    session.commit()


def test_t1b_a_requested_disbursement_comes_back_equal():
    original = _disbursement()
    _committed(lambda session: session.disbursements.add(original))

    session = _session()
    assert session.disbursements.get("d-1") == original
    assert session.disbursements.get("no-existe") is None
    session.rollback()


def test_t1b_a_decided_disbursement_keeps_its_code_digest_and_refused_attempts():
    original = _disbursement()
    original.refused_approval_attempts.append(
        RefusedApprovalAttempt("cobrador-1", Role.COLLECTOR, NOW, "quien_origina_no_aprueba")
    )
    original.status = DisbursementStatus.APPROVED
    original.approved_by = original.decided_by = "admin-1"
    original.decided_at = NOW
    original.decision_reason = "cliente recurrente"
    original.code = ConfirmationCode.issue("ABCD1234", "d-1", "cliente-1", NOW, timedelta(hours=1))
    _committed(lambda session: session.disbursements.add(original))

    session = _session()
    assert session.disbursements.get("d-1") == original
    session.rollback()


def test_t1b_saving_twice_stores_each_refused_attempt_once():
    _committed(lambda session: session.disbursements.add(_disbursement()))

    def refuse(session: PostgresSession, reason: str) -> None:
        stored = session.disbursements.get("d-1")
        stored.refused_approval_attempts.append(
            RefusedApprovalAttempt("cobrador-1", Role.COLLECTOR, NOW, reason)
        )
        session.disbursements.save(stored)

    _committed(lambda session: refuse(session, "primero"))
    _committed(lambda session: refuse(session, "segundo"))

    session = _session()
    attempts = session.disbursements.get("d-1").refused_approval_attempts
    session.rollback()
    assert [attempt.reason for attempt in attempts] == ["primero", "segundo"]


def test_t1b_two_transactions_changing_the_same_disbursement_do_not_overwrite_each_other():
    _committed(lambda session: session.disbursements.add(_disbursement()))
    loser, winner = _session(), _session()
    stale = loser.disbursements.get("d-1")
    fresh = winner.disbursements.get("d-1")
    fresh.status = DisbursementStatus.REJECTED
    fresh.decided_by, fresh.decided_at, fresh.decision_reason = "admin-1", NOW, "sin cupo"
    winner.disbursements.save(fresh)
    winner.commit()

    stale.status = DisbursementStatus.APPROVED
    with pytest.raises(StaleWrite):
        loser.disbursements.save(stale)
    loser.rollback()

    session = _session()
    assert session.disbursements.get("d-1").status is DisbursementStatus.REJECTED
    session.rollback()


def test_t1b_a_confirmed_disbursement_its_loan_and_its_box_survive_a_restart():
    built = build_container(Settings(ledger_url=APP_URL), FakeClock(), SimulatedNotifier())
    flow = Flow(TestClient(create_app(built)), built.notifier)
    opening = flow.cash_balance()
    disbursement = flow.approved()
    code = flow.issued_code(disbursement["id"])
    assert flow.confirm(disbursement["id"], code).status_code == 200

    restarted_container = build_container(Settings(ledger_url=APP_URL), FakeClock(), SimulatedNotifier())
    restarted = Flow(TestClient(create_app(restarted_container)), restarted_container.notifier)

    detail = restarted.read(disbursement["id"])
    assert detail["status"] == "CONFIRMADO"
    assert detail["loan"]["principal_cents"] == disbursement["amount_cents"]
    assert restarted.cash_balance() == opening - disbursement["amount_cents"]
    assert len(restarted.ledger(disbursement["id"])) == 1
    # The in-memory store plays no part once the database is configured.
    assert built.store.tables.disbursements == {}
