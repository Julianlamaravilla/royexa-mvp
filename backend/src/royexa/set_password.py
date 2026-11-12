"""Sets the password of a seeded user: python -m royexa.set_password <user>

For the first deployment (T6-P2): with ROYEXA_REQUIRE_CHANGED_PASSWORDS=1 the server seeds no
demonstration password and refuses to start while one remains, so the real ones are set here
first. It connects with ROYEXA_LEDGER_URL, replaces the hash, clears the demo mark and any
lock, and ends the user's sessions. The password is read without echo and never printed.
"""

from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path
from datetime import UTC, datetime

import psycopg

from royexa.identity_access.domain import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH
from royexa.identity_access.passwords import PasswordHasher
from royexa.seed import directory_for


def provision_password(
    url: str, user_id: str, password: str, hasher: PasswordHasher | None = None
) -> None:
    seed = os.environ.get("ROYEXA_SEED", "demo")
    directory_file = os.environ.get("ROYEXA_DIRECTORY_FILE")
    if user_id not in {u.id for u in directory_for(seed, Path(directory_file) if directory_file else None).users()}:
        raise ValueError(f"unknown user: {user_id}")
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ValueError(f"the password needs at least {MIN_PASSWORD_LENGTH} characters")
    now = datetime.now(UTC)
    stored = (hasher or PasswordHasher()).hash(password)
    with psycopg.connect(url) as connection:
        connection.execute(
            "INSERT INTO credential (user_id, password_hash, is_demo, changed_at) "
            "VALUES (%s, %s, false, %s) ON CONFLICT (user_id) DO UPDATE SET "
            "password_hash = EXCLUDED.password_hash, is_demo = false, failed_attempts = 0, "
            "locked_until = NULL, changed_at = EXCLUDED.changed_at",
            (user_id, stored, now),
        )
        connection.execute(
            "UPDATE session SET revoked_at = %s WHERE user_id = %s AND revoked_at IS NULL",
            (now, user_id),
        )


def main(argv: list[str]) -> int:
    url = os.environ.get("ROYEXA_LEDGER_URL")
    if len(argv) != 2 or not url:
        print("usage: ROYEXA_LEDGER_URL=... python -m royexa.set_password <user>", file=sys.stderr)
        return 2
    password = getpass.getpass("New password: ")
    if password != getpass.getpass("Repeat it: "):
        print("The two passwords differ.", file=sys.stderr)
        return 1
    try:
        provision_password(url, argv[1], password)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print(f"Password of {argv[1]} set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
