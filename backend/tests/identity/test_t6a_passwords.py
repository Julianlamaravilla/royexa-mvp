"""T6a, T6-P2: passwords are kept as salted scrypt hashes and checked in constant time."""

import os
import subprocess
import sys

from royexa.identity_access.passwords import PasswordHasher

CHEAP = PasswordHasher(n=16)


def test_t6a_the_hash_is_not_the_password_and_names_its_own_cost():
    stored = CHEAP.hash("una-clave-larga-y-secreta")

    assert "una-clave-larga-y-secreta" not in stored
    algorithm, n, r, p, salt, digest = stored.split("$")
    assert (algorithm, n, r, p) == ("scrypt", "16", "8", "1")
    assert salt and digest


def test_t6a_the_right_password_verifies_and_a_wrong_one_does_not():
    stored = CHEAP.hash("una-clave-larga-y-secreta")

    assert CHEAP.verify("una-clave-larga-y-secreta", stored) is True
    assert CHEAP.verify("otra-clave-distinta", stored) is False
    assert CHEAP.verify("", stored) is False


def test_t6a_two_hashes_of_the_same_password_differ_by_their_salt():
    assert CHEAP.hash("misma-clave-larga") != CHEAP.hash("misma-clave-larga")


def test_t6a_a_hash_keeps_verifying_after_the_default_cost_changes():
    stored = PasswordHasher(n=16).hash("clave-con-su-coste")

    assert PasswordHasher(n=32).verify("clave-con-su-coste", stored) is True


def test_t6a_a_malformed_or_foreign_hash_never_verifies():
    for stored in ("", "texto", "scrypt$x$8$1$AA$AA", "bcrypt$16$8$1$AA$AA", "scrypt$16$8$1$AA"):
        assert CHEAP.verify("cualquier-clave", stored) is False, stored


def test_t6a_a_tampered_digest_does_not_verify():
    stored = CHEAP.hash("clave-que-no-se-toca")
    algorithm, n, r, p, salt, digest = stored.split("$")
    flipped = ("A" if digest[0] != "A" else "B") + digest[1:]

    assert CHEAP.verify("clave-que-no-se-toca", "$".join((algorithm, n, r, p, salt, flipped))) is False


def test_t6a_the_default_cost_is_the_strong_one_unless_the_environment_lowers_it():
    """The test run lowers it through ROYEXA_SCRYPT_N; a clean environment must not."""
    clean = {"PATH": os.environ["PATH"]}
    result = subprocess.run(
        [sys.executable, "-I", "-c", "from royexa.identity_access.passwords import PasswordHasher; print(PasswordHasher().n)"],
        env=clean,
        capture_output=True,
        text=True,
        check=True,
    )

    assert int(result.stdout) >= 2**14
