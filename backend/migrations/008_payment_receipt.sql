-- T4 (RF-06, CA-11): a payment receipt waits in the outbox like the disbursement notices.
-- A notice names its disbursement or its payment, never both; one notice per payment.
-- The grants of outbox_message do not change. Safe to repeat.

ALTER TABLE outbox_message ALTER COLUMN disbursement_id DROP NOT NULL;
ALTER TABLE outbox_message ADD COLUMN IF NOT EXISTS payment_id text;

ALTER TABLE outbox_message DROP CONSTRAINT IF EXISTS outbox_message_names_its_operation;
ALTER TABLE outbox_message ADD CONSTRAINT outbox_message_names_its_operation CHECK (
    (kind = 'COMPROBANTE_PAGO' AND payment_id IS NOT NULL AND disbursement_id IS NULL)
    OR (kind <> 'COMPROBANTE_PAGO' AND disbursement_id IS NOT NULL AND payment_id IS NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS outbox_message_one_per_payment
    ON outbox_message (payment_id) WHERE payment_id IS NOT NULL;
