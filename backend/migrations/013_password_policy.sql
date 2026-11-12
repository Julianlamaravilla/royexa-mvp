-- T6b (T6-P2, T6-P3): the failed-attempt count, the lock and the date of the last change
-- live on the credential, and the application role may now update it (a user changes their
-- own password). It still cannot delete one. Safe to repeat.

ALTER TABLE credential ADD COLUMN IF NOT EXISTS failed_attempts integer NOT NULL DEFAULT 0
    CHECK (failed_attempts >= 0);
ALTER TABLE credential ADD COLUMN IF NOT EXISTS locked_until timestamptz;
ALTER TABLE credential ADD COLUMN IF NOT EXISTS changed_at timestamptz;

GRANT UPDATE ON credential TO royexa_app;
