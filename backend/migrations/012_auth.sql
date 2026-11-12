-- T6a (T6-P1, T6-P2): credentials and sessions.
-- A credential holds a salted scrypt hash, never the password; `is_demo` is true while it is
-- still the documented demonstration password (T6b can refuse to start with those).
-- A session holds the SHA-256 digest of its token, never the token. The application role
-- cannot delete either; a session changes only when it is revoked. Safe to repeat.

CREATE TABLE IF NOT EXISTS credential (
    user_id       text PRIMARY KEY,
    password_hash text NOT NULL CHECK (password_hash LIKE 'scrypt$%'),
    is_demo       boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS session (
    token_hash text PRIMARY KEY CHECK (length(token_hash) = 64),
    user_id    text NOT NULL,
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL CHECK (expires_at > created_at),
    revoked_at timestamptz
);

CREATE INDEX IF NOT EXISTS session_by_user ON session (user_id);

REVOKE ALL ON credential, session FROM PUBLIC;
REVOKE ALL ON credential, session FROM royexa_app;
GRANT SELECT, INSERT ON credential TO royexa_app;
GRANT SELECT, INSERT, UPDATE ON session TO royexa_app;
