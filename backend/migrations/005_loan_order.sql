-- T2b: loans are listed in the order they were granted. Safe to repeat.

ALTER TABLE loan ADD COLUMN IF NOT EXISTS seq bigint GENERATED ALWAYS AS IDENTITY;
