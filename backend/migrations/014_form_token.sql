-- T7a (T7-P4): one-time form tokens. Each is tied to the session that asked for it, accepted
-- once, and keeps the result of the work so a repeat shows it instead of repeating the
-- effect. Only the SHA-256 digest of the token is stored. The application role inserts and
-- updates them; it never deletes. Safe to repeat.

CREATE TABLE IF NOT EXISTS form_token (
    token_hash   text PRIMARY KEY CHECK (length(token_hash) = 64),
    session_hash text NOT NULL REFERENCES session (token_hash),
    purpose      text NOT NULL,
    created_at   timestamptz NOT NULL,
    used_at      timestamptz,
    outcome_kind text CHECK (outcome_kind IN ('ok', 'error')),
    outcome_text text,
    outcome_next text,
    CHECK ((outcome_kind IS NULL) = (outcome_text IS NULL)),
    CHECK ((outcome_kind IS NULL) = (outcome_next IS NULL))
);

CREATE INDEX IF NOT EXISTS form_token_by_session ON form_token (session_hash);

REVOKE ALL ON form_token FROM PUBLIC;
REVOKE ALL ON form_token FROM royexa_app;
GRANT SELECT, INSERT, UPDATE ON form_token TO royexa_app;
