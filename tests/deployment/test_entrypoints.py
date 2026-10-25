"""SPEC-05, TKT-0501: the entrypoints refuse a secret anyone but its owner can read (REQ-0514)."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
ENTRYPOINTS = ROOT / "docker" / "entrypoints"

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="file modes need a POSIX filesystem (CI runs Linux)"
)


def _run(entrypoint: str, secrets: Path, marker: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sh", str(ENTRYPOINTS / entrypoint), "touch", str(marker)],
        env={
            "PATH": "/usr/bin:/bin",
            "GS_SECRETS_SRC": str(secrets),
            "GS_SECRETS_DST": str(secrets.parent / "copies"),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


@pytest.mark.parametrize("entrypoint", ["grindstone.sh", "agent-host.sh"])
@pytest.mark.parametrize("mode", [0o644, 0o640, 0o604, 0o660])
def test_entrypoint_refuses_readable_secret(tmp_path: Path, entrypoint: str, mode: int) -> None:
    """AC-0514-1."""
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "a_good_one").write_text("x", encoding="utf-8")
    (secrets / "a_good_one").chmod(0o600)
    readable = secrets / "host_control_key"
    readable.write_text("x", encoding="utf-8")
    readable.chmod(mode)
    marker = tmp_path / "service-started"

    result = _run(entrypoint, secrets, marker)

    assert result.returncode != 0
    assert str(readable) in result.stderr
    assert f"mode {mode:o}" in result.stderr
    assert not marker.exists()
    assert not (tmp_path / "copies").exists()
