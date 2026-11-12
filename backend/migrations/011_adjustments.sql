-- T5d (CA-08, RN-04, T5-P4): the compensating entry. An error is corrected with a new
-- AJUSTE entry that names the entry it corrects and states its motive; the original is
-- never touched and the ledger stays append-only (ADR-001). An adjustment is signed and
-- never zero; every other entry stays positive. Safe to repeat.

ALTER TABLE ledger_entry ADD COLUMN IF NOT EXISTS adjusts_entry_id text REFERENCES ledger_entry (id);

ALTER TABLE ledger_entry DROP CONSTRAINT IF EXISTS ledger_entry_amount_cents_check;
ALTER TABLE ledger_entry DROP CONSTRAINT IF EXISTS ledger_entry_amount_by_type;
ALTER TABLE ledger_entry ADD CONSTRAINT ledger_entry_amount_by_type CHECK (
    (entry_type = 'AJUSTE' AND amount_cents <> 0)
    OR (entry_type <> 'AJUSTE' AND amount_cents > 0)
);

ALTER TABLE ledger_entry DROP CONSTRAINT IF EXISTS ledger_entry_type_known;
ALTER TABLE ledger_entry ADD CONSTRAINT ledger_entry_type_known
    CHECK (entry_type IN ('DESEMBOLSO', 'DESEMBOLSO_CADUCADO', 'PAGO', 'AJUSTE'));

ALTER TABLE ledger_entry DROP CONSTRAINT IF EXISTS ledger_entry_names_its_operation;
ALTER TABLE ledger_entry ADD CONSTRAINT ledger_entry_names_its_operation CHECK (
    (entry_type = 'PAGO'
        AND payment_id IS NOT NULL AND payment_method IS NOT NULL
        AND disbursement_id IS NULL AND adjusts_entry_id IS NULL)
    OR (entry_type = 'AJUSTE'
        AND adjusts_entry_id IS NOT NULL AND reason IS NOT NULL AND length(btrim(reason)) > 0
        AND disbursement_id IS NULL AND payment_id IS NULL AND payment_method IS NULL)
    OR (entry_type NOT IN ('PAGO', 'AJUSTE')
        AND disbursement_id IS NOT NULL
        AND payment_id IS NULL AND payment_method IS NULL AND adjusts_entry_id IS NULL)
);

CREATE INDEX IF NOT EXISTS ledger_entry_by_adjusted_entry
    ON ledger_entry (adjusts_entry_id) WHERE adjusts_entry_id IS NOT NULL;
