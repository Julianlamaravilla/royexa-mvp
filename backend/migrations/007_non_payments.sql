-- T3b (RF-01, CA-02): a non-payment with its reason and its commitment date.
-- Append-only for the application role: a visit that happened is never edited.
-- Runs as royexa_migrator, the table owner; every statement is safe to repeat.

CREATE TABLE IF NOT EXISTS non_payment (
    id              text PRIMARY KEY,
    loan_id         text NOT NULL REFERENCES loan (id),
    client_id       text NOT NULL,
    collector_id    text NOT NULL,
    reason          text NOT NULL CHECK (length(btrim(reason)) > 0),
    commitment_date date NOT NULL,
    device_time     timestamptz NOT NULL,
    server_time     timestamptz NOT NULL,
    seq             bigint GENERATED ALWAYS AS IDENTITY
);

CREATE INDEX IF NOT EXISTS non_payment_by_loan ON non_payment (loan_id);

REVOKE ALL ON non_payment FROM PUBLIC;
REVOKE ALL ON non_payment FROM royexa_app;
GRANT SELECT, INSERT ON non_payment TO royexa_app;
