"""Password hashing with scrypt from the standard library (T6-P2): a salt per password and
the cost written into the stored value, so raising it later never invalidates a hash."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass

# 2**14 is the production cost; a test run lowers it through the environment to stay fast.
SCRYPT_N = int(os.environ.get("ROYEXA_SCRYPT_N", str(2**14)))
SCRYPT_R = 8
SCRYPT_P = 1
KEY_BYTES = 32
SALT_BYTES = 16
MEMORY_LIMIT = 64 * 1024 * 1024


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


@dataclass(frozen=True)
class PasswordHasher:
    n: int = SCRYPT_N
    r: int = SCRYPT_R
    p: int = SCRYPT_P

    def hash(self, password: str) -> str:
        salt = os.urandom(SALT_BYTES)
        digest = self._derive(password, salt, self.n, self.r, self.p)
        return f"scrypt${self.n}${self.r}${self.p}${_b64(salt)}${_b64(digest)}"

    def verify(self, password: str, stored: str) -> bool:
        """Constant-time comparison; anything malformed or foreign is simply not a match."""
        try:
            algorithm, n, r, p, salt, expected = stored.split("$")
            if algorithm != "scrypt":
                return False
            digest = self._derive(
                password, base64.b64decode(salt, validate=True), int(n), int(r), int(p)
            )
            return hmac.compare_digest(digest, base64.b64decode(expected, validate=True))
        except ValueError:
            return False

    @staticmethod
    def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
        return hashlib.scrypt(
            password.encode(), salt=salt, n=n, r=r, p=p, dklen=KEY_BYTES, maxmem=MEMORY_LIMIT
        )
