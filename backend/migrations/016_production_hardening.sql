-- T10b: a managed PostgreSQL (Supabase) exposes the public schema through its own API to the
-- roles `anon` and `authenticated`. The ledger must not be readable that way, so:
--   1. those roles lose every privilege on what exists and on what the owner creates later;
--   2. every table has row-level security, with one policy that lets only `royexa_app` through
--      (its privileges are still the append-only ones of each migration, ADR-001).
-- Safe to repeat. A migration that adds a table must be followed by this file, which sorts
-- last: it runs on every start and covers whatever exists by then.

DO $$
DECLARE
    exposed text;
    item record;
BEGIN
    FOREACH exposed IN ARRAY ARRAY['anon', 'authenticated', 'service_role'] LOOP
        IF EXISTS (SELECT FROM pg_roles WHERE rolname = exposed) THEN
            EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %I', exposed);
            EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM %I', exposed);
            EXECUTE format('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM %I', exposed);
            EXECUTE format(
                'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM %I', exposed);
        END IF;
    END LOOP;

    FOR item IN
        SELECT c.relname AS name
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'r' AND pg_get_userbyid(c.relowner) = current_user
    LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', item.name);
        IF NOT EXISTS (
            SELECT FROM pg_policies WHERE schemaname = 'public' AND tablename = item.name
        ) THEN
            EXECUTE format(
                'CREATE POLICY royexa_app_only ON public.%I FOR ALL TO royexa_app '
                'USING (true) WITH CHECK (true)', item.name);
        END IF;
    END LOOP;
END
$$;
