"""Composition root: the only place that knows which adapter fills each port."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta

from royexa.adapters.memory import InMemoryStore, InMemoryUnitOfWork
from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.closing.application import CashCloseQueries, CloseCashBox
from royexa.clients.application import ClientQueries, RegisterClient
from royexa.identity_access.domain import Directory
from royexa.loans.application import (
    LoanQueries,
    PaymentQueries,
    RegisterNonPayment,
    RegisterPayment,
    VisitQueries,
)
from royexa.notifications.dispatcher import NoticeQueries, NotificationDispatcher
from royexa.notifications.ports import Notifier
from royexa.sales.application import (
    ApproveDisbursement,
    ConfirmDisbursement,
    GrantRenewalException,
    RejectDisbursement,
    RequestDisbursement,
    SalesContext,
    SalesQueries,
)
from royexa.seed import seed_clients, seed_directory, seed_loans, seed_store
from royexa.shared.calendar import BusinessCalendar
from royexa.shared.clock import Clock, SystemClock

DEFAULT_CODE_TTL_MINUTES = 60
DEFAULT_TIMEZONE = "UTC"


@dataclass(frozen=True)
class Settings:
    code_ttl: timedelta = timedelta(minutes=DEFAULT_CODE_TTL_MINUTES)
    notifier_failing: bool = False
    ledger_url: str | None = None
    timezone: str = DEFAULT_TIMEZONE

    @classmethod
    def from_env(cls) -> Settings:
        minutes = int(os.environ.get("ROYEXA_CODE_TTL_MINUTES", DEFAULT_CODE_TTL_MINUTES))
        return cls(
            code_ttl=timedelta(minutes=minutes),
            notifier_failing=os.environ.get("ROYEXA_NOTIFIER_FAILING") == "1",
            ledger_url=os.environ.get("ROYEXA_LEDGER_URL"),
            timezone=os.environ.get("ROYEXA_TIMEZONE", DEFAULT_TIMEZONE),
        )


@dataclass(frozen=True)
class Container:
    directory: Directory
    register_client: RegisterClient
    client_queries: ClientQueries
    loan_queries: LoanQueries
    register_payment: RegisterPayment
    payment_queries: PaymentQueries
    register_non_payment: RegisterNonPayment
    visit_queries: VisitQueries
    close_cash_box: CloseCashBox
    cash_close_queries: CashCloseQueries
    store: InMemoryStore
    notifier: Notifier
    request: RequestDisbursement
    approve: ApproveDisbursement
    reject: RejectDisbursement
    confirm: ConfirmDisbursement
    grant_exception: GrantRenewalException
    queries: SalesQueries
    dispatcher: NotificationDispatcher
    notices: NoticeQueries
    context: SalesContext


def build_container(
    settings: Settings | None = None,
    clock: Clock | None = None,
    notifier: Notifier | None = None,
) -> Container:
    settings = settings or Settings()
    clock = clock or SystemClock()
    notifier = notifier or SimulatedNotifier(
        sink=lambda line: print(line, flush=True), failing=settings.notifier_failing
    )
    store = seed_store()
    if settings.ledger_url:
        from royexa.adapters.postgres_state import seed_database

        seed_database(settings.ledger_url, seed_loans(), seed_clients())
    directory = seed_directory()
    calendar = BusinessCalendar.in_zone(settings.timezone)

    def ledger_session():
        # Imported here so the in-memory demo and its tests need no database driver.
        from royexa.adapters.postgres_state import PostgresSession

        return PostgresSession(settings.ledger_url)

    def unit_of_work() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(store, ledger_session if settings.ledger_url else None)

    context = SalesContext(unit_of_work, clock, directory, settings.code_ttl, calendar=calendar)
    return Container(
        directory=directory,
        register_client=RegisterClient(unit_of_work, directory),
        client_queries=ClientQueries(unit_of_work),
        loan_queries=LoanQueries(unit_of_work),
        register_payment=RegisterPayment(unit_of_work, clock, directory, calendar),
        payment_queries=PaymentQueries(unit_of_work),
        register_non_payment=RegisterNonPayment(unit_of_work, clock, directory, calendar),
        visit_queries=VisitQueries(unit_of_work, clock, directory, calendar),
        close_cash_box=CloseCashBox(unit_of_work, clock, directory, calendar),
        cash_close_queries=CashCloseQueries(unit_of_work),
        store=store,
        notifier=notifier,
        request=RequestDisbursement(context),
        approve=ApproveDisbursement(context),
        reject=RejectDisbursement(context),
        confirm=ConfirmDisbursement(context),
        grant_exception=GrantRenewalException(context),
        queries=SalesQueries(unit_of_work, clock, directory, calendar),
        dispatcher=NotificationDispatcher(unit_of_work, notifier, clock),
        notices=NoticeQueries(unit_of_work),
        context=context,
    )
