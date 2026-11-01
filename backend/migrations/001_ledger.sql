-- ADR-001: the ledger is append-only for the application role.
-- ADR-004, INV-02: one entry per disbursement and type.
-- Runs as royexa_migrator, the table owner. The password is a local-only demo value.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'royexa_app') THEN
        CREATE ROLE royexa_app LOGIN PASSWORD 'royexa_app';
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS ledger_entry (
    id              text PRIMARY KEY,
    disbursement_id text NOT NULL,
    entry_type      text NOT NULL CHECK (entry_type IN ('DESEMBOLSO', 'DESEMBOLSO_CADUCADO')),
    amount_cents    bigint NOT NULL CHECK (amount_cents > 0),
    cash_box_id     text NOT NULL,
    actor_id        text NOT NULL,
    device_time     timestamptz NOT NULL,
    server_time     timestamptz NOT NULL,
    reason          text,
    CONSTRAINT ledger_entry_one_per_disbursement_and_type UNIQUE (disbursement_id, entry_type),
    CONSTRAINT ledger_entry_expiry_has_reason
        CHECK (entry_type <> 'DESEMBOLSO_CADUCADO' OR reason IS NOT NULL)
);

REVOKE ALL ON ledger_entry FROM PUBLIC;
REVOKE ALL ON ledger_entry FROM royexa_app;
GRANT SELECT, INSERT ON ledger_entry TO royexa_app;
