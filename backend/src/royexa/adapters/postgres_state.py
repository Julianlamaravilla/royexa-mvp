"""Cash boxes, loans, renewal exceptions and notices on PostgreSQL (T1a, ADR-002).

All four repositories share the connection of the ledger session, so entry, deduction,
loan and notice commit together or not at all.
"""

from __future__ import annotations

from datetime import date

import psycopg
from psycopg import errors
from psycopg.types.json import Jsonb

from royexa.adapters.postgres_ledger import PostgresLedgerSession
from royexa.cash_box.domain import CashBox, CashClose
from royexa.clients.domain import Client
from royexa.identity_access.domain import Role
from royexa.identity_access.domain import Credential, Session
from royexa.loans.domain import (
    Allocation,
    Installment,
    Loan,
    LoanTerms,
    NonPayment,
    Payment,
    RenewalException,
)
from royexa.sales.domain import (
    ConfirmationCode,
    Disbursement,
    DisbursementStatus,
    RefusedApprovalAttempt,
)
from royexa.shared.errors import StaleWrite
from royexa.shared.money import Money
from royexa.shared.payments import PaymentMethod
from royexa.shared.outbox import NoticeKind, NoticeStatus, OutboxMessage

_BOX = "id, collector_id, day, opening_balance_cents, balance_cents, closed"
_EXCEPTION = "id, client_id, prior_loan_id, granted_by, reason, granted_at, consumed_by"
_NOTICE = (
    "id, kind, client_id, disbursement_id, created_at, payload, status, attempts, "
    "last_error, sent_at, payment_id"
)


def _update(connection: psycopg.Connection, sql: str, params: tuple, what: str) -> int:
    """A concurrent update that committed first surfaces as a serialization failure."""
    try:
        return connection.execute(sql, params).rowcount
    except errors.SerializationFailure as error:
        raise StaleWrite(what) from error


class PostgresCashRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection
        self._versions: dict[str, int] = {}

    def get(self, box_id: str) -> CashBox | None:
        row = self._connection.execute(
            f"SELECT {_BOX}, version FROM cash_box WHERE id = %s", (box_id,)
        ).fetchone()
        if row is None:
            return None
        self._versions[row[0]] = row[6]
        return CashBox(row[0], row[1], row[2], Money(row[3]), Money(row[4]), row[5])

    def box_of_day(self, collector_id: str, day: date) -> CashBox | None:
        row = self._connection.execute(
            f"SELECT {_BOX}, version FROM cash_box WHERE collector_id = %s AND day = %s",
            (collector_id, day),
        ).fetchone()
        if row is None:
            return None
        self._versions[row[0]] = row[6]
        return CashBox(row[0], row[1], row[2], Money(row[3]), Money(row[4]), row[5])

    def save(self, box: CashBox) -> None:
        """Optimistic: the write wins only if nobody changed the box since it was read. Two
        first movements of a day race for the same row; the second one loses."""
        values = (box.opening_balance.cents, box.balance.cents, box.closed, box.id)
        if box.id in self._versions:
            written = _update(
                self._connection,
                "UPDATE cash_box SET opening_balance_cents = %s, balance_cents = %s, "
                "closed = %s, version = version + 1 WHERE id = %s AND version = %s",
                (*values, self._versions[box.id]),
                f"cash_box/{box.id}",
            )
            if written == 0:
                raise StaleWrite(f"cash_box/{box.id}")
            self._versions[box.id] += 1
        else:
            try:
                self._connection.execute(
                    "INSERT INTO cash_box (opening_balance_cents, balance_cents, closed, id, "
                    "collector_id, day) VALUES (%s, %s, %s, %s, %s, %s)",
                    (*values, box.collector_id, box.day),
                )
            except errors.UniqueViolation as error:
                raise StaleWrite(f"cash_box/{box.collector_id}/{box.day}") from error
            self._versions[box.id] = 0


class PostgresCashCloseRepository:
    _COLUMNS = (
        "id, cash_box_id, collector_id, day, expected_cents, delivered_cents, closed_by, "
        "device_time, server_time"
    )

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def add(self, close: CashClose) -> None:
        try:
            self._connection.execute(
                f"INSERT INTO cash_close ({self._COLUMNS}) VALUES ({', '.join(['%s'] * 9)})",
                (
                    close.id,
                    close.cash_box_id,
                    close.collector_id,
                    close.day,
                    close.expected.cents,
                    close.delivered.cents,
                    close.closed_by,
                    close.device_time,
                    close.server_time,
                ),
            )
        except errors.UniqueViolation as error:
            raise StaleWrite(f"cash_close/{close.cash_box_id}") from error

    def all(self, collector_id: str | None = None, day: date | None = None) -> list[CashClose]:
        filters = {"collector_id": collector_id, "day": day}
        chosen = {column: value for column, value in filters.items() if value is not None}
        where = " AND ".join(f"{column} = %s" for column in chosen)
        rows = self._connection.execute(
            f"SELECT {self._COLUMNS} FROM cash_close {'WHERE ' + where if chosen else ''} "
            "ORDER BY seq",
            tuple(chosen.values()),
        )
        return [
            CashClose(id, box, collector, d, Money(expected), Money(delivered), by, device, server)
            for id, box, collector, d, expected, delivered, by, device, server in rows
        ]


class PostgresAuthRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def credential(self, user_id: str) -> Credential | None:
        row = self._connection.execute(
            "SELECT user_id, password_hash, is_demo FROM credential WHERE user_id = %s",
            (user_id,),
        ).fetchone()
        return Credential(*row) if row else None

    def add_session(self, session: Session) -> None:
        self._connection.execute(
            "INSERT INTO session (token_hash, user_id, created_at, expires_at, revoked_at) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                session.token_hash,
                session.user_id,
                session.created_at,
                session.expires_at,
                session.revoked_at,
            ),
        )

    def session(self, token_hash: str) -> Session | None:
        row = self._connection.execute(
            "SELECT token_hash, user_id, created_at, expires_at, revoked_at FROM session "
            "WHERE token_hash = %s",
            (token_hash,),
        ).fetchone()
        return Session(*row) if row else None

    def save_session(self, session: Session) -> None:
        self._connection.execute(
            "UPDATE session SET revoked_at = %s WHERE token_hash = %s",
            (session.revoked_at, session.token_hash),
        )


class PostgresClientRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def add(self, client: Client) -> None:
        self._connection.execute(
            "INSERT INTO client (id, name, route_id) VALUES (%s, %s, %s)",
            (client.id, client.name, client.route_id),
        )

    def get(self, client_id: str) -> Client | None:
        row = self._connection.execute(
            "SELECT id, name, route_id FROM client WHERE id = %s", (client_id,)
        ).fetchone()
        return Client(*row) if row else None

    def all(self) -> list[Client]:
        rows = self._connection.execute("SELECT id, name, route_id FROM client ORDER BY seq")
        return [Client(*row) for row in rows]


class PostgresLoanRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def add(self, loan: Loan) -> None:
        self._connection.execute(
            "INSERT INTO loan (id, client_id, disbursement_id, principal_cents, interest_cents) "
            "VALUES (%s, %s, %s, %s, %s)",
            (loan.id, loan.client_id, loan.disbursement_id, loan.principal.cents, loan.interest.cents),
        )
        for item in loan.installments:
            self._connection.execute(
                "INSERT INTO loan_installment (loan_id, sequence, due_date, amount_cents, "
                "paid_cents) VALUES (%s, %s, %s, %s, %s)",
                (loan.id, item.sequence, item.due_date, item.amount.cents, item.paid.cents),
            )

    def save(self, loan: Loan) -> None:
        """A concurrent payment on the same installment loses with a serialization failure."""
        for item in loan.installments:
            _update(
                self._connection,
                "UPDATE loan_installment SET paid_cents = %s WHERE loan_id = %s AND sequence = %s",
                (item.paid.cents, loan.id, item.sequence),
                f"loan/{loan.id}",
            )

    def get(self, loan_id: str) -> Loan | None:
        return next(iter(self._loans("WHERE id = %s", (loan_id,))), None)

    def unsettled_for_client(self, client_id: str) -> Loan | None:
        return next((loan for loan in self.for_client(client_id) if not loan.is_settled), None)

    def for_client(self, client_id: str) -> list[Loan]:
        return self._loans("WHERE client_id = %s", (client_id,))

    def _loans(self, where: str, params: tuple) -> list[Loan]:
        rows = self._connection.execute(
            "SELECT id, client_id, disbursement_id, principal_cents, interest_cents "
            f"FROM loan {where} ORDER BY seq",
            params,
        ).fetchall()
        loans = []
        for loan_id, client_id, disbursement_id, principal, interest in rows:
            installments = self._connection.execute(
                "SELECT sequence, due_date, amount_cents, paid_cents FROM loan_installment "
                "WHERE loan_id = %s ORDER BY sequence",
                (loan_id,),
            )
            schedule = tuple(
                Installment(seq, due, Money(amount), Money(paid))
                for seq, due, amount, paid in installments
            )
            loans.append(
                Loan(loan_id, client_id, disbursement_id, Money(principal), Money(interest), schedule)
            )
        return loans

    def add_exception(self, exception: RenewalException) -> None:
        self._connection.execute(
            f"INSERT INTO renewal_exception ({_EXCEPTION}) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            _exception_values(exception),
        )

    def save_exception(self, exception: RenewalException) -> None:
        _update(
            self._connection,
            "UPDATE renewal_exception SET consumed_by = %s WHERE id = %s",
            (exception.consumed_by, exception.id),
            f"renewal_exception/{exception.id}",
        )

    def get_exception(self, exception_id: str) -> RenewalException | None:
        row = self._connection.execute(
            f"SELECT {_EXCEPTION} FROM renewal_exception WHERE id = %s", (exception_id,)
        ).fetchone()
        return RenewalException(*row) if row else None

    def open_exception_for(self, client_id: str) -> RenewalException | None:
        row = self._connection.execute(
            f"SELECT {_EXCEPTION} FROM renewal_exception "
            "WHERE client_id = %s AND consumed_by IS NULL ORDER BY seq LIMIT 1",
            (client_id,),
        ).fetchone()
        return RenewalException(*row) if row else None


def _exception_values(exception: RenewalException) -> tuple:
    return (
        exception.id,
        exception.client_id,
        exception.prior_loan_id,
        exception.granted_by,
        exception.reason,
        exception.granted_at,
        exception.consumed_by,
    )


class PostgresPaymentRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def add(self, payment: Payment) -> None:
        self._connection.execute(
            "INSERT INTO payment (id, loan_id, client_id, collector_id, amount_cents, method, "
            "device_time, server_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                payment.id,
                payment.loan_id,
                payment.client_id,
                payment.collector_id,
                payment.amount.cents,
                payment.method.value,
                payment.device_time,
                payment.server_time,
            ),
        )
        for allocation in payment.allocations:
            self._connection.execute(
                "INSERT INTO payment_allocation (payment_id, sequence, amount_cents) "
                "VALUES (%s, %s, %s)",
                (payment.id, allocation.sequence, allocation.amount.cents),
            )

    def for_loan(self, loan_id: str) -> list[Payment]:
        rows = self._connection.execute(
            "SELECT id, loan_id, client_id, collector_id, amount_cents, method, device_time, "
            "server_time FROM payment WHERE loan_id = %s ORDER BY seq",
            (loan_id,),
        ).fetchall()
        payments = []
        for id, loan, client, collector, amount, method, device, server in rows:
            allocations = tuple(
                Allocation(sequence, Money(cents))
                for sequence, cents in self._connection.execute(
                    "SELECT sequence, amount_cents FROM payment_allocation "
                    "WHERE payment_id = %s ORDER BY sequence",
                    (id,),
                )
            )
            payments.append(
                Payment(
                    id, loan, client, collector, Money(amount), PaymentMethod(method),
                    device, server, allocations,
                )
            )
        return payments


class PostgresNonPaymentRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def add(self, item: NonPayment) -> None:
        self._connection.execute(
            "INSERT INTO non_payment (id, loan_id, client_id, collector_id, reason, "
            "commitment_date, device_time, server_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                item.id,
                item.loan_id,
                item.client_id,
                item.collector_id,
                item.reason,
                item.commitment_date,
                item.device_time,
                item.server_time,
            ),
        )

    def for_loan(self, loan_id: str) -> list[NonPayment]:
        rows = self._connection.execute(
            "SELECT id, loan_id, client_id, collector_id, reason, commitment_date, device_time, "
            "server_time FROM non_payment WHERE loan_id = %s ORDER BY seq",
            (loan_id,),
        )
        return [NonPayment(*row) for row in rows]


class PostgresOutbox:
    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def add(self, message: OutboxMessage) -> None:
        self._connection.execute(
            f"INSERT INTO outbox_message ({_NOTICE}) VALUES ({', '.join(['%s'] * 11)})",
            _notice_values(message),
        )

    def get(self, message_id: str) -> OutboxMessage | None:
        return next(iter(self._messages("WHERE id = %s", (message_id,))), None)

    def save(self, message: OutboxMessage) -> None:
        _update(
            self._connection,
            "UPDATE outbox_message SET payload = %s, status = %s, attempts = %s, "
            "last_error = %s, sent_at = %s WHERE id = %s",
            (
                Jsonb(message.payload),
                message.status.value,
                message.attempts,
                message.last_error,
                message.sent_at,
                message.id,
            ),
            f"outbox_message/{message.id}",
        )

    def pending(self) -> list[OutboxMessage]:
        return self._messages("WHERE status = %s", (NoticeStatus.PENDING.value,))

    def all(
        self, disbursement_id: str | None = None, payment_id: str | None = None
    ) -> list[OutboxMessage]:
        filters = {"disbursement_id": disbursement_id, "payment_id": payment_id}
        chosen = {column: value for column, value in filters.items() if value is not None}
        where = " AND ".join(f"{column} = %s" for column in chosen)
        return self._messages(f"WHERE {where}" if chosen else "", tuple(chosen.values()))

    def _messages(self, where: str, params: tuple) -> list[OutboxMessage]:
        rows = self._connection.execute(
            f"SELECT {_NOTICE} FROM outbox_message {where} ORDER BY seq", params
        )
        return [
            OutboxMessage(
                id, NoticeKind(kind), client, disbursement, created, payload,
                NoticeStatus(status), attempts, error, sent, payment,
            )
            for id, kind, client, disbursement, created, payload, status, attempts, error, sent, payment
            in rows
        ]


def _notice_values(message: OutboxMessage) -> tuple:
    return (
        message.id,
        message.kind.value,
        message.client_id,
        message.disbursement_id,
        message.created_at,
        Jsonb(message.payload),
        message.status.value,
        message.attempts,
        message.last_error,
        message.sent_at,
        message.payment_id,
    )


_DISBURSEMENT = (
    "id, client_id, route_id, collector_id, requested_by, requested_at, principal_cents, "
    "term_days, installment_count, interest_cents, status, renewal_exception_id, approved_by, "
    "decided_by, decided_at, decision_reason, code_digest, code_expires_at, confirmed_by, "
    "resolved_at, loan_id"
)
_MUTABLE = (
    "status, renewal_exception_id, approved_by, decided_by, decided_at, decision_reason, "
    "code_digest, code_expires_at, confirmed_by, resolved_at, loan_id"
).split(", ")


def _mutable_values(item: Disbursement) -> tuple:
    return (
        item.status.value,
        item.renewal_exception_id,
        item.approved_by,
        item.decided_by,
        item.decided_at,
        item.decision_reason,
        item.code.digest if item.code else None,
        item.code.expires_at if item.code else None,
        item.confirmed_by,
        item.resolved_at,
        item.loan_id,
    )


class PostgresDisbursementRepository:
    """Optimistic like the cash box: a save wins only if the row is as it was read."""

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection
        self._read: dict[str, tuple[int, int]] = {}  # id -> (version, stored attempts)

    def add(self, item: Disbursement) -> None:
        self._connection.execute(
            f"INSERT INTO disbursement ({_DISBURSEMENT}) VALUES ({', '.join(['%s'] * 21)})",
            (
                item.id,
                item.client_id,
                item.route_id,
                item.collector_id,
                item.requested_by,
                item.requested_at,
                item.terms.principal.cents,
                item.terms.term_days,
                item.terms.installment_count,
                item.interest.cents,
                *_mutable_values(item),
            ),
        )
        self._append_attempts(item, 0)
        self._read[item.id] = (0, len(item.refused_approval_attempts))

    def get(self, disbursement_id: str) -> Disbursement | None:
        row = self._connection.execute(
            f"SELECT {_DISBURSEMENT}, version FROM disbursement WHERE id = %s", (disbursement_id,)
        ).fetchone()
        if row is None:
            return None
        attempts = [
            RefusedApprovalAttempt(actor, Role(role), at, reason)
            for actor, role, at, reason in self._connection.execute(
                "SELECT actor_id, actor_role, at, reason FROM refused_approval_attempt "
                "WHERE disbursement_id = %s ORDER BY sequence",
                (disbursement_id,),
            )
        ]
        self._read[disbursement_id] = (row[21], len(attempts))
        code = ConfirmationCode(row[16], row[17]) if row[16] else None
        return Disbursement(
            id=row[0],
            client_id=row[1],
            route_id=row[2],
            collector_id=row[3],
            requested_by=row[4],
            requested_at=row[5],
            terms=LoanTerms(Money(row[6]), row[7], row[8]),
            interest=Money(row[9]),
            status=DisbursementStatus(row[10]),
            renewal_exception_id=row[11],
            approved_by=row[12],
            decided_by=row[13],
            decided_at=row[14],
            decision_reason=row[15],
            code=code,
            confirmed_by=row[18],
            resolved_at=row[19],
            loan_id=row[20],
            refused_approval_attempts=attempts,
        )

    def save(self, item: Disbursement) -> None:
        version, stored = self._read[item.id]
        assignments = ", ".join(f"{column} = %s" for column in _MUTABLE)
        written = _update(
            self._connection,
            f"UPDATE disbursement SET {assignments}, version = version + 1 "
            "WHERE id = %s AND version = %s",
            (*_mutable_values(item), item.id, version),
            f"disbursement/{item.id}",
        )
        if written == 0:
            raise StaleWrite(f"disbursement/{item.id}")
        self._append_attempts(item, stored)
        self._read[item.id] = (version + 1, len(item.refused_approval_attempts))

    def _append_attempts(self, item: Disbursement, already_stored: int) -> None:
        for sequence, attempt in enumerate(
            item.refused_approval_attempts[already_stored:], start=already_stored + 1
        ):
            self._connection.execute(
                "INSERT INTO refused_approval_attempt (disbursement_id, sequence, actor_id, "
                "actor_role, at, reason) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    item.id,
                    sequence,
                    attempt.actor_id,
                    attempt.actor_role.value,
                    attempt.at,
                    attempt.reason,
                ),
            )


class PostgresSession(PostgresLedgerSession):
    """The ledger session plus the mutable state, in one transaction."""

    def __init__(self, url: str) -> None:
        super().__init__(url)
        self.clients = PostgresClientRepository(self._connection)
        self.cash_closes = PostgresCashCloseRepository(self._connection)
        self.auth = PostgresAuthRepository(self._connection)
        self.disbursements = PostgresDisbursementRepository(self._connection)
        self.cash = PostgresCashRepository(self._connection)
        self.loans = PostgresLoanRepository(self._connection)
        self.payments = PostgresPaymentRepository(self._connection)
        self.non_payments = PostgresNonPaymentRepository(self._connection)
        self.outbox = PostgresOutbox(self._connection)


def seed_database(
    url: str, loans: list[Loan], clients: list[Client], credentials: list[Credential]
) -> None:
    """Demo data (RES-02). Rows that already exist are left as they are."""
    with psycopg.connect(url) as connection:
        for credential in credentials:
            connection.execute(
                "INSERT INTO credential (user_id, password_hash, is_demo) VALUES (%s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (credential.user_id, credential.password_hash, credential.is_demo),
            )
        for client in clients:
            connection.execute(
                "INSERT INTO client (id, name, route_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (client.id, client.name, client.route_id),
            )
        for loan in loans:
            if connection.execute("SELECT 1 FROM loan WHERE id = %s", (loan.id,)).fetchone():
                continue
            session_loans = PostgresLoanRepository(connection)
            session_loans.add(loan)
