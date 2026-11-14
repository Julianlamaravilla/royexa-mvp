"""Composition root: the only place that knows which adapter fills each port."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

from royexa.adapters.memory import InMemoryStore, InMemoryUnitOfWork, Tables
from royexa.adapters.simulated_notifier import SimulatedNotifier
from royexa.closing.application import (
    CashCloseQueries,
    CloseCashBox,
    DiscrepancyQueries,
    RegisterAdjustment,
)
from royexa.clients.application import ClientQueries, RegisterClient
from royexa.identity_access.application import DEFAULT_SESSION_TTL, Authenticator
from royexa.identity_access.domain import DemoPasswordsInUse, Directory
from royexa.identity_access.passwords import PasswordHasher
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
from royexa.seed import (
    seed_clients,
    seed_credentials,
    directory_for,
    seed_loans,
    seed_store,
)
from royexa.shared.calendar import BusinessCalendar
from royexa.web.forms import FormTokens
from royexa.shared.clock import Clock, SystemClock

DEFAULT_CODE_TTL_MINUTES = 60
DEFAULT_TIMEZONE = "UTC"


@dataclass(frozen=True)
class Settings:
    code_ttl: timedelta = timedelta(minutes=DEFAULT_CODE_TTL_MINUTES)
    notifier_failing: bool = False
    ledger_url: str | None = None
    timezone: str = DEFAULT_TIMEZONE
    session_ttl: timedelta = DEFAULT_SESSION_TTL
    currency_symbol: str = ""
    require_changed_passwords: bool = False
    dispatch_seconds: float = 30.0
    seed: str = "demo"
    directory_file: Path | None = None

    @classmethod
    def from_env(cls) -> Settings:
        seed = os.environ.get("ROYEXA_SEED", "demo")
        if seed not in ("demo", "pilot"):
            raise ValueError(f"ROYEXA_SEED must be 'demo' or 'pilot', not {seed!r}")
        directory_file = os.environ.get("ROYEXA_DIRECTORY_FILE")
        minutes = int(os.environ.get("ROYEXA_CODE_TTL_MINUTES", DEFAULT_CODE_TTL_MINUTES))
        return cls(
            code_ttl=timedelta(minutes=minutes),
            notifier_failing=os.environ.get("ROYEXA_NOTIFIER_FAILING") == "1",
            ledger_url=os.environ.get("ROYEXA_LEDGER_URL"),
            timezone=os.environ.get("ROYEXA_TIMEZONE", DEFAULT_TIMEZONE),
            require_changed_passwords=os.environ.get("ROYEXA_REQUIRE_CHANGED_PASSWORDS") == "1",
            currency_symbol=os.environ.get("ROYEXA_CURRENCY_SYMBOL", ""),
            dispatch_seconds=float(os.environ.get("ROYEXA_DISPATCH_SECONDS", "30")),
            seed=seed,
            directory_file=Path(directory_file) if directory_file else None,
            session_ttl=timedelta(
                hours=float(os.environ.get("ROYEXA_SESSION_HOURS", DEFAULT_SESSION_TTL.total_seconds() / 3600))
            ),
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
    discrepancy_queries: DiscrepancyQueries
    authenticator: Authenticator
    form_tokens: FormTokens
    currency_symbol: str
    calendar: BusinessCalendar
    register_adjustment: RegisterAdjustment
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
    ping: Callable[[], None]


def ensure_production_ready(settings: Settings) -> None:
    """Checked by the production entry point (royexa.main), not by every container the tests
    build: the strict mode also refuses the known password of the application role."""
    if (
        settings.require_changed_passwords
        and settings.ledger_url
        and urlparse(settings.ledger_url).password == "royexa_app"
    ):
        raise DemoPasswordsInUse(
            "the strict mode refuses the known password of the royexa_app role: set ROYEXA_APP_PASSWORD"
        )


def database_ping(url: str | None) -> Callable[[], None]:
    """What /health asks of the database: a query that answers, within five seconds."""

    def ping() -> None:
        if url:
            import psycopg

            with psycopg.connect(url, connect_timeout=5) as connection:
                connection.execute("SELECT 1")

    return ping


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
    if settings.require_changed_passwords and not settings.ledger_url:
        raise DemoPasswordsInUse(
            "the strict mode keeps passwords in the database: set ROYEXA_LEDGER_URL"
        )
    hasher = PasswordHasher()
    pilot = settings.seed == "pilot"
    # T10-P5: a pilot start keeps no demonstration client, loan or password.
    store = InMemoryStore(Tables()) if pilot else seed_store(hasher)
    if settings.ledger_url and not pilot:
        from royexa.adapters.postgres_state import seed_database

        # T6-P2: the strict mode seeds no demonstration password at all.
        demo = [] if settings.require_changed_passwords else seed_credentials(hasher)
        seed_database(settings.ledger_url, seed_loans(), seed_clients(), demo)
    directory = directory_for(settings.seed, settings.directory_file)
    calendar = BusinessCalendar.in_zone(settings.timezone)

    def ledger_session():
        # Imported here so the in-memory demo and its tests need no database driver.
        from royexa.adapters.postgres_state import PostgresSession

        return PostgresSession(settings.ledger_url)

    def unit_of_work() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(store, ledger_session if settings.ledger_url else None)

    if settings.require_changed_passwords:
        with unit_of_work() as uow:
            remaining = uow.auth.demo_users()
        if remaining:
            raise DemoPasswordsInUse(
                "the strict mode refuses demonstration passwords; set the real ones with "
                "python -m royexa.set_password for: " + ", ".join(remaining)
            )

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
        discrepancy_queries=DiscrepancyQueries(unit_of_work, clock, calendar),
        authenticator=Authenticator(unit_of_work, clock, directory, hasher, settings.session_ttl),
        form_tokens=FormTokens(unit_of_work, clock),
        currency_symbol=settings.currency_symbol,
        calendar=calendar,
        register_adjustment=RegisterAdjustment(unit_of_work, clock, directory, calendar),
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
        ping=database_ping(settings.ledger_url),
    )
