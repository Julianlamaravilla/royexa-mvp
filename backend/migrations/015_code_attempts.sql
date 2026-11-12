-- T10a (T10-P3): five wrong confirmation codes in a row lock the request for 15 minutes.
-- The count and the end of the lock live on the disbursement. Idempotent: it runs on every
-- start; the application role already updates this table (003) and never deletes.
ALTER TABLE disbursement
    ADD COLUMN IF NOT EXISTS failed_code_attempts integer NOT NULL DEFAULT 0
        CHECK (failed_code_attempts BETWEEN 0 AND 4),
    ADD COLUMN IF NOT EXISTS code_locked_until timestamptz;
