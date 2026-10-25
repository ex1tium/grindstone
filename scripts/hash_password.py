"""Hash the operator password with Argon2id for `make secrets` (SPEC-05, REQ-0513).

`uv run --frozen python -m scripts.hash_password` prints one PHC-format hash
on stdout. The password is read from the terminal without echo, asked twice;
without a terminal, one line is read from standard input, byte by byte so
nothing after it is consumed. It is never taken from argv or the
environment. `--generate` hashes a random password nobody sees, for a
development or CI stack that never logs in.

The parameters are RFC 9106's second recommended option: 64 MiB, 3 passes,
4 lanes. SPEC-10 reads them back from the hash when it verifies.
"""

import argparse
import getpass
import os
import secrets
import sys
from collections.abc import Sequence

from argon2 import PasswordHasher
from argon2.low_level import Type

TIME_COST = 3
MEMORY_COST_KIB = 64 * 1024
PARALLELISM = 4


def hasher() -> PasswordHasher:
    """Argon2id with SPEC-05's parameters."""
    return PasswordHasher(
        time_cost=TIME_COST,
        memory_cost=MEMORY_COST_KIB,
        parallelism=PARALLELISM,
        hash_len=32,
        salt_len=16,
        type=Type.ID,
    )


def _read_line(fd: int) -> str:
    """One line from `fd`, without its newline, reading no byte past it."""
    data = bytearray()
    while (byte := os.read(fd, 1)) and byte != b"\n":
        data += byte
    return data.decode("utf-8").removesuffix("\r")


def _ask() -> str:
    first = getpass.getpass("Operator password: ")
    if getpass.getpass("Again: ") != first:
        raise SystemExit("hash_password: the passwords differ")
    return first


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hash_password", description=__doc__)
    parser.add_argument(
        "--generate", action="store_true", help="hash a random password that is never shown"
    )
    args = parser.parse_args(argv)
    if args.generate:
        password = secrets.token_urlsafe(32)
    elif sys.stdin.isatty():
        password = _ask()
    else:
        password = _read_line(sys.stdin.fileno())
    if not password:
        sys.stderr.write("hash_password: the password is empty\n")
        return 1
    sys.stdout.write(hasher().hash(password) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
