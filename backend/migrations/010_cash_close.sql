-- T5b (RF-02, CA-03, RN-02): the close of a day's cash box, with its signed discrepancy.
-- Append-only for the application role: a close is never edited or deleted, and a box
-- closes once. The ledger gets an index to add up one box's entries. Safe to repeat.

CREATE TABLE IF NOT EXISTS cash_close (
    id              text PRIMARY KEY,
    cash_box_id     text NOT NULL UNIQUE REFERENCES cash_box (id),
    collector_id    text NOT NULL,
    day             date NOT NULL,
    expected_cents  bigint NOT NULL,
    delivered_cents bigint NOT NULL CHECK (delivered_cents >= 0),
    closed_by       text NOT NULL,
    device_time     timestamptz NOT NULL,
    server_time     timestamptz NOT NULL,
    seq             bigint GENERATED ALWAYS AS IDENTITY
);

CREATE INDEX IF NOT EXISTS cash_close_by_day ON cash_close (day, collector_id);
CREATE INDEX IF NOT EXISTS ledger_entry_by_cash_box ON ledger_entry (cash_box_id);

REVOKE ALL ON cash_close FROM PUBLIC;
REVOKE ALL ON cash_close FROM royexa_app;
GRANT SELECT, INSERT ON cash_close TO royexa_app;
