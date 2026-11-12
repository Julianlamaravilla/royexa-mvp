-- T5a (RN-02, T5-P2): one cash box per collector and day, opened by the first movement.
-- A box that was never closed no longer blocks the next day's: the old "one open box per
-- collector" index becomes "one box per collector and day". Safe to repeat.

ALTER TABLE cash_box ADD COLUMN IF NOT EXISTS day date;
UPDATE cash_box SET day = (now() AT TIME ZONE 'UTC')::date WHERE day IS NULL;
ALTER TABLE cash_box ALTER COLUMN day SET NOT NULL;

DROP INDEX IF EXISTS cash_box_one_open_per_collector;
CREATE UNIQUE INDEX IF NOT EXISTS cash_box_one_per_collector_and_day
    ON cash_box (collector_id, day);
