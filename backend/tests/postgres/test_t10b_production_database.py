"""T10b1: what the database must look like when it is not the project's own (Supabase exposes
the public schema to `anon` and `authenticated`), and the password of the application role.
Needs PostgreSQL."""

import psycopg
import pytest

from royexa.bootstrap import Settings, build_container
from royexa.migrate import MIGRATOR_URL, apply_migrations
from royexa.adapters.simulated_notifier import SimulatedNotifier
from support import FakeClock
from royexa.set_password import provision_password

pytestmark = pytest.mark.postgres
APP = "postgresql://royexa_app:{}@localhost:55432/royexa"
TABLES = (
    "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
    "WHERE n.nspname = 'public' AND c.relkind = 'r'"
)


@pytest.fixture
def supabase_like():
    """The roles and default grants a Supabase project brings."""
    with psycopg.connect(MIGRATOR_URL, autocommit=True) as owner:
        for role in ("anon", "authenticated"):
            owner.execute(
                f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{role}') "
                f"THEN CREATE ROLE {role} NOLOGIN; END IF; END $$"
            )
            owner.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
            owner.execute(f"GRANT ALL ON ALL TABLES IN SCHEMA public TO {role}")
            owner.execute(
                f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {role}"
            )
    yield
    with psycopg.connect(MIGRATOR_URL, autocommit=True) as owner:
        for role in ("anon", "authenticated"):
            owner.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM {role}")


def test_t10b_the_migrations_close_every_table_to_the_roles_the_platform_exposes(supabase_like):
    apply_migrations()

    with psycopg.connect(MIGRATOR_URL) as owner:
        tables = [row[0] for row in owner.execute(TABLES)]
        assert len(tables) > 10
        for role in ("anon", "authenticated"):
            for table in tables:
                allowed = owner.execute(
                    "SELECT has_table_privilege(%s, %s, 'SELECT') OR has_table_privilege(%s, %s, 'INSERT')",
                    (role, table, role, table),
                ).fetchone()[0]
                assert not allowed, f"{role} can reach {table}"


def test_t10b_a_table_created_later_by_the_owner_is_closed_too(supabase_like):
    apply_migrations()
    with psycopg.connect(MIGRATOR_URL, autocommit=True) as owner:
        owner.execute("CREATE TABLE IF NOT EXISTS t10b_probe (id int)")
        try:
            assert not owner.execute(
                "SELECT has_table_privilege('anon', 't10b_probe', 'SELECT')"
            ).fetchone()[0]
        finally:
            owner.execute("DROP TABLE t10b_probe")


def test_t10b_every_table_has_row_level_security_with_a_policy_for_the_application(supabase_like):
    apply_migrations()

    with psycopg.connect(MIGRATOR_URL) as owner:
        for (table,) in owner.execute(TABLES).fetchall():
            secured = owner.execute(
                "SELECT relrowsecurity FROM pg_class WHERE oid = %s::regclass", (table,)
            ).fetchone()[0]
            policies = owner.execute(
                "SELECT count(*) FROM pg_policies WHERE tablename = %s AND 'royexa_app' = ANY(roles)",
                (table,),
            ).fetchone()[0]
            assert secured and policies == 1, table


def test_t10b_the_application_role_still_works_with_row_level_security(container):
    from support import Flow  # the whole vertical flow runs as royexa_app
    from fastapi.testclient import TestClient
    from royexa.api import create_app

    flow = Flow(TestClient(create_app(container)), SimulatedNotifier())
    assert flow.requested().get("status") == "SOLICITADO"


def test_t10b_applying_the_migrations_again_keeps_one_policy_per_table(supabase_like):
    apply_migrations()
    apply_migrations()

    with psycopg.connect(MIGRATOR_URL) as owner:
        assert owner.execute(
            "SELECT max(n) FROM (SELECT count(*) n FROM pg_policies WHERE schemaname = 'public' "
            "GROUP BY tablename) t"
        ).fetchone()[0] == 1


def test_t10b_the_password_of_the_application_role_comes_from_the_environment(monkeypatch):
    secret = "una-clave-larga-solo-para-la-prueba-0001"
    stored = "SELECT rolpassword FROM pg_authid WHERE rolname = 'royexa_app'"
    with psycopg.connect(MIGRATOR_URL) as owner:
        before = owner.execute(stored).fetchone()[0]
    monkeypatch.setenv("ROYEXA_APP_PASSWORD", secret)
    try:
        apply_migrations()
        psycopg.connect(APP.format(secret)).close()
        with psycopg.connect(MIGRATOR_URL) as owner:
            after = owner.execute(stored).fetchone()[0]
        assert after != before and after.startswith("SCRAM-SHA-256$"), "stored as a hash, changed"
    finally:
        with psycopg.connect(MIGRATOR_URL, autocommit=True) as owner:
            owner.execute("ALTER ROLE royexa_app PASSWORD 'royexa_app'")


def test_t10b_a_short_password_for_the_application_role_is_refused(monkeypatch):
    monkeypatch.setenv("ROYEXA_APP_PASSWORD", "corta")

    with pytest.raises(ValueError, match="ROYEXA_APP_PASSWORD"):
        apply_migrations()


def test_t10b_the_pilot_start_seeds_nothing_and_a_provisioned_user_can_enter(supabase_like, monkeypatch):
    from database import reset_database

    from fastapi.testclient import TestClient

    from royexa.api import create_app

    secret = "una-clave-larga-solo-para-la-prueba-0002"
    monkeypatch.setenv("ROYEXA_APP_PASSWORD", secret)
    monkeypatch.setenv("ROYEXA_SEED", "pilot")
    try:
        apply_migrations()
        reset_database()
        settings = Settings(seed="pilot", ledger_url=APP.format(secret), require_changed_passwords=True)
        container = build_container(settings, FakeClock(), SimulatedNotifier())
        assert container.client_queries.all() == []
        with psycopg.connect(MIGRATOR_URL) as owner:
            assert owner.execute("SELECT count(*) FROM credential").fetchone()[0] == 0
            assert owner.execute("SELECT count(*) FROM loan").fetchone()[0] == 0

        provision_password(MIGRATOR_URL, "admin-1", "una-contrasena-de-prueba-123")
        ok = TestClient(create_app(container)).post(
            "/v1/auth/login", json={"user_id": "admin-1", "password": "una-contrasena-de-prueba-123"}
        )
        assert ok.status_code == 200
    finally:
        with psycopg.connect(MIGRATOR_URL, autocommit=True) as owner:
            owner.execute("ALTER ROLE royexa_app PASSWORD 'royexa_app'")
        reset_database()
