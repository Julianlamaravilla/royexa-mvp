-- T1b: disbursements and their refused approval attempts (RN-06) in PostgreSQL.
-- The confirmation code is stored as a digest only (RN-03). The application role may
-- insert and update disbursements and insert attempts; nothing is ever deleted.
-- Runs as royexa_migrator, the table owner; every statement is safe to repeat.

CREATE TABLE IF NOT EXISTS disbursement (
    id                   text PRIMARY KEY,
    client_id            text NOT NULL,
    route_id             text NOT NULL,
    collector_id         text NOT NULL,
    requested_by         text NOT NULL,
    requested_at         timestamptz NOT NULL,
    principal_cents      bigint NOT NULL CHECK (principal_cents > 0),
    term_days            integer NOT NULL,
    installment_count    integer NOT NULL,
    interest_cents       bigint NOT NULL CHECK (interest_cents >= 0),
    status               text NOT NULL,
    renewal_exception_id text,
    approved_by          text,
    decided_by           text,
    decided_at           timestamptz,
    decision_reason      text,
    code_digest          text,
    code_expires_at      timestamptz,
    confirmed_by         text,
    resolved_at          timestamptz,
    loan_id              text,
    version              integer NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS refused_approval_attempt (
    disbursement_id text NOT NULL REFERENCES disbursement (id),
    sequence        integer NOT NULL,
    actor_id        text NOT NULL,
    actor_role      text NOT NULL,
    at              timestamptz NOT NULL,
    reason          text NOT NULL,
    PRIMARY KEY (disbursement_id, sequence)
);

REVOKE ALL ON disbursement, refused_approval_attempt FROM PUBLIC;
REVOKE ALL ON disbursement, refused_approval_attempt FROM royexa_app;
GRANT SELECT, INSERT, UPDATE ON disbursement TO royexa_app;
GRANT SELECT, INSERT ON refused_approval_attempt TO royexa_app;
