"""SPEC-05, TKT-0501: `make secrets` and the operator password hash (REQ-0513)."""

import hashlib
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from argon2 import PasswordHasher
from argon2.low_level import Type
from scripts import hash_password

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "scripts" / "make_secrets.sh"
SECRETS = (
    "postgres_password",
    "mcp_token_key",
    "host_control_key",
    "host_event_key",
    "session_key",
    "operator_password_hash",
    "github_app_key",
    "claude_oauth_token",
)
"""Every file in SPEC-05's secret table."""

posix_only = pytest.mark.skipif(
    sys.platform == "win32", reason="file modes need a POSIX filesystem (CI runs Linux)"
)


def _make_secrets(directory: Path, stdin: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "GRINDSTONE_SECRETS_DIR": str(directory)}
    return subprocess.run(
        ["bash", str(SCRIPT)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=300,
    )


def _snapshot(directory: Path) -> dict[str, tuple[int, int, str]]:
    out: dict[str, tuple[int, int, str]] = {}
    for path in sorted(directory.iterdir()):
        info = path.stat()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        out[path.name] = (stat.S_IMODE(info.st_mode), info.st_mtime_ns, digest)
    return out


@posix_only
def test_make_secrets_idempotent(tmp_path: Path) -> None:
    """AC-0513-1."""
    password = "correct horse battery staple"  # noqa: S105 - a test password, not a secret
    app_key = tmp_path / "app.pem"
    app_key.write_text("-----BEGIN PRIVATE KEY-----\nnot-a-key\n", encoding="utf-8")
    token = tmp_path / "token"
    token.write_text("not-a-token\n", encoding="utf-8")
    directory = tmp_path / "secrets"

    first = _make_secrets(directory, f"{password}\n{app_key}\n{token}\n")
    assert first.returncode == 0, first.stderr

    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert sorted(p.name for p in directory.iterdir()) == sorted(SECRETS)
    for path in directory.iterdir():
        assert stat.S_IMODE(path.stat().st_mode) == 0o600, path.name

    # The password is stored only as an Argon2id hash with SPEC-05's parameters.
    stored = (directory / "operator_password_hash").read_text(encoding="utf-8").strip()
    assert stored.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert PasswordHasher().verify(stored, password)
    for path in directory.iterdir():
        assert password.encode() not in path.read_bytes(), path.name
    assert password not in first.stdout + first.stderr

    assert (directory / "github_app_key").read_bytes() == app_key.read_bytes()
    assert (directory / "claude_oauth_token").read_bytes() == token.read_bytes()
    keys = [(directory / n).read_text(encoding="utf-8") for n in SECRETS[:5]]
    assert len(set(keys)) == 5
    assert all(len(k) == 43 and "=" not in k and "\n" not in k for k in keys)

    # Run again: nothing changes, not even a modification time.
    before = _snapshot(directory)
    second = _make_secrets(directory, "another password\n/nonexistent\n/nonexistent\n")
    assert second.returncode == 0, second.stderr
    assert _snapshot(directory) == before
    assert "created" not in second.stdout


@posix_only
def test_make_secrets_without_input(tmp_path: Path) -> None:
    """In CI no terminal answers: a random, unshown password and empty files for the rest."""
    directory = tmp_path / "secrets"
    result = _make_secrets(directory, "")
    assert result.returncode == 0, result.stderr
    stored = (directory / "operator_password_hash").read_text(encoding="utf-8")
    assert stored.startswith("$argon2id$")
    assert (directory / "github_app_key").read_bytes() == b""
    assert (directory / "claude_oauth_token").read_bytes() == b""


@posix_only
def test_make_secrets_refuses_a_readable_secret_without_a_terminal(tmp_path: Path) -> None:
    """An M0 checkout's 0644 secret is tightened only with the operator's confirmation."""
    directory = tmp_path / "secrets"
    directory.mkdir(mode=0o700)
    old = directory / "postgres_password"
    old.write_text("m0-password", encoding="utf-8")
    old.chmod(0o644)
    result = _make_secrets(directory, "")
    assert result.returncode != 0
    assert str(old) in result.stderr
    assert old.read_text(encoding="utf-8") == "m0-password"
    assert stat.S_IMODE(old.stat().st_mode) == 0o644


def test_hash_password_reads_one_line_and_uses_spec_parameters(
    capsys: pytest.CaptureFixture[str],
) -> None:
    read, write = os.pipe()
    os.write(write, b"s3cret-line\nleft for the next reader\n")
    os.close(write)
    try:
        assert hash_password._read_line(read) == "s3cret-line"  # pyright: ignore[reportPrivateUsage]
        assert os.read(read, 100) == b"left for the next reader\n"
    finally:
        os.close(read)

    hasher = hash_password.hasher()
    assert hasher.type is Type.ID
    assert (hasher.memory_cost, hasher.time_cost, hasher.parallelism) == (65536, 3, 4)

    assert hash_password.main(["--generate"]) == 0
    printed = capsys.readouterr()
    assert printed.out.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert printed.out.count("\n") == 1
