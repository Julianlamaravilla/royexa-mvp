-- T3a (RF-01, RN-01): payments, their allocation to installments and their ledger entry.
-- The ledger stays append-only (ADR-001); a payment entry names its payment, not a
-- disbursement. Payments are append-only for the application role. Safe to repeat.

ALTER TABLE ledger_entry ALTER COLUMN disbursement_id DROP NOT NULL;
ALTER TABLE ledger_entry ADD COLUMN IF NOT EXISTS payment_id text;
ALTER TABLE ledger_entry ADD COLUMN IF NOT EXISTS payment_method text;

ALTER TABLE ledger_entry DROP CONSTRAINT IF EXISTS ledger_entry_entry_type_check;
ALTER TABLE ledger_entry DROP CONSTRAINT IF EXISTS ledger_entry_type_known;
ALTER TABLE ledger_entry ADD CONSTRAINT ledger_entry_type_known
    CHECK (entry_type IN ('DESEMBOLSO', 'DESEMBOLSO_CADUCADO', 'PAGO'));

ALTER TABLE ledger_entry DROP CONSTRAINT IF EXISTS ledger_entry_names_its_operation;
ALTER TABLE ledger_entry ADD CONSTRAINT ledger_entry_names_its_operation CHECK (
    (entry_type = 'PAGO' AND payment_id IS NOT NULL AND payment_method IS NOT NULL
        AND disbursement_id IS NULL)
    OR (entry_type <> 'PAGO' AND disbursement_id IS NOT NULL AND payment_id IS NULL
        AND payment_method IS NULL)
);

-- INV-02: one entry per payment.
CREATE UNIQUE INDEX IF NOT EXISTS ledger_entry_one_per_payment
    ON ledger_entry (payment_id) WHERE payment_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS payment (
    id           text PRIMARY KEY,
    loan_id      text NOT NULL REFERENCES loan (id),
    client_id    text NOT NULL,
    collector_id text NOT NULL,
    amount_cents bigint NOT NULL CHECK (amount_cents > 0),
    method       text NOT NULL CHECK (method IN ('EFECTIVO', 'TRANSFERENCIA')),
    device_time  timestamptz NOT NULL,
    server_time  timestamptz NOT NULL,
    seq          bigint GENERATED ALWAYS AS IDENTITY
);

CREATE INDEX IF NOT EXISTS payment_by_loan ON payment (loan_id);

CREATE TABLE IF NOT EXISTS payment_allocation (
    payment_id   text NOT NULL REFERENCES payment (id),
    sequence     integer NOT NULL,
    amount_cents bigint NOT NULL CHECK (amount_cents > 0),
    PRIMARY KEY (payment_id, sequence)
);

REVOKE ALL ON payment, payment_allocation FROM PUBLIC;
REVOKE ALL ON payment, payment_allocation FROM royexa_app;
GRANT SELECT, INSERT ON payment, payment_allocation TO royexa_app;
