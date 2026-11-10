-- T1a: cash boxes, loans, renewal exceptions and notices (outbox) in PostgreSQL.
-- Mutable state: the application role may insert and update, never delete.
-- Runs as royexa_migrator, the table owner; every statement is safe to repeat.

CREATE TABLE IF NOT EXISTS cash_box (
    id                    text PRIMARY KEY,
    collector_id          text NOT NULL,
    opening_balance_cents bigint NOT NULL,
    balance_cents         bigint NOT NULL,
    closed                boolean NOT NULL DEFAULT false,
    version               integer NOT NULL DEFAULT 0
);

-- RN-02: a collector has at most one open box.
CREATE UNIQUE INDEX IF NOT EXISTS cash_box_one_open_per_collector
    ON cash_box (collector_id) WHERE NOT closed;

CREATE TABLE IF NOT EXISTS loan (
    id              text PRIMARY KEY,
    client_id       text NOT NULL,
    disbursement_id text,
    principal_cents bigint NOT NULL CHECK (principal_cents > 0),
    interest_cents  bigint NOT NULL CHECK (interest_cents >= 0)
);

CREATE INDEX IF NOT EXISTS loan_by_client ON loan (client_id);

CREATE TABLE IF NOT EXISTS loan_installment (
    loan_id      text NOT NULL REFERENCES loan (id),
    sequence     integer NOT NULL CHECK (sequence > 0),
    due_date     date NOT NULL,
    amount_cents bigint NOT NULL CHECK (amount_cents > 0),
    paid_cents   bigint NOT NULL DEFAULT 0 CHECK (paid_cents >= 0),
    PRIMARY KEY (loan_id, sequence)
);

CREATE TABLE IF NOT EXISTS renewal_exception (
    id            text PRIMARY KEY,
    client_id     text NOT NULL,
    prior_loan_id text NOT NULL REFERENCES loan (id),
    granted_by    text NOT NULL,
    reason        text NOT NULL,
    granted_at    timestamptz NOT NULL,
    consumed_by   text,
    seq           bigint GENERATED ALWAYS AS IDENTITY
);

CREATE TABLE IF NOT EXISTS outbox_message (
    id              text PRIMARY KEY,
    kind            text NOT NULL,
    client_id       text NOT NULL,
    disbursement_id text NOT NULL,
    created_at      timestamptz NOT NULL,
    payload         jsonb NOT NULL DEFAULT '{}',
    status          text NOT NULL,
    attempts        integer NOT NULL DEFAULT 0,
    last_error      text,
    sent_at         timestamptz,
    seq             bigint GENERATED ALWAYS AS IDENTITY
);

DO $$
DECLARE
    state_table text;
BEGIN
    FOREACH state_table IN ARRAY ARRAY[
        'cash_box', 'loan', 'loan_installment', 'renewal_exception', 'outbox_message'
    ] LOOP
        EXECUTE format('REVOKE ALL ON %I FROM PUBLIC', state_table);
        EXECUTE format('REVOKE ALL ON %I FROM royexa_app', state_table);
        EXECUTE format('GRANT SELECT, INSERT, UPDATE ON %I TO royexa_app', state_table);
    END LOOP;
END
$$;
