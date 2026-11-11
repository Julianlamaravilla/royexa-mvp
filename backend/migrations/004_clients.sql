-- T2a (RF-05): the clients the administrator registers on a route.
-- The application role inserts and reads; a client is never updated or deleted here.
-- Runs as royexa_migrator, the table owner; every statement is safe to repeat.

CREATE TABLE IF NOT EXISTS client (
    id       text PRIMARY KEY,
    name     text NOT NULL CHECK (length(btrim(name)) > 0),
    route_id text NOT NULL,
    seq      bigint GENERATED ALWAYS AS IDENTITY
);

REVOKE ALL ON client FROM PUBLIC;
REVOKE ALL ON client FROM royexa_app;
GRANT SELECT, INSERT ON client TO royexa_app;
