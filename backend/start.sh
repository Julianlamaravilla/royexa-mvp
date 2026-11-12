#!/bin/sh
# Start of the production container (T10b2): apply the migrations, then serve.
# A database needs both URLs: the migrator owns the schema, the application only uses it.
set -eu

PYTHON="${ROYEXA_PYTHON:-python}"

if [ -n "${ROYEXA_LEDGER_URL:-}" ]; then
    if [ -z "${ROYEXA_MIGRATOR_URL:-}" ]; then
        echo "ROYEXA_LEDGER_URL is set but ROYEXA_MIGRATOR_URL is not: refusing to serve an unmigrated database." >&2
        exit 1
    fi
    "$PYTHON" -m royexa.migrate > /dev/null
fi

exec "$PYTHON" -m uvicorn royexa.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'
