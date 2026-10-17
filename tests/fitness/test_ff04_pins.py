"""FF-04: everything is pinned exactly."""

import json
from pathlib import Path

import pytest
from scripts.ff.pins import violations

from tests.fitness.helpers import FIXTURES, REPO

DIGEST = "@sha256:" + "a" * 64
SHA = "b" * 40


def test_repository_is_pinned() -> None:
    assert violations(REPO) == []


def test_floating_tag_fixture_fails_the_build() -> None:
    found = violations(FIXTURES / "floating_tag")
    assert found == ["compose.yaml:4: image not pinned by digest: postgres:18"]


@pytest.mark.parametrize(
    ("path", "content", "expected"),
    [
        ("Dockerfile", "FROM python:3.14-slim\n", "base image not pinned by digest"),
        ("Dockerfile", f"FROM python{DIGEST} AS base\nFROM base\n", None),
        ("Dockerfile", "COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /bin/\n", "COPY --from image"),
        ("compose.yaml", f"services:\n  db:\n    image: postgres:18{DIGEST}\n", None),
        (".github/workflows/ci.yml", "    - uses: actions/checkout@v5\n", "not pinned to a commit"),
        (".github/workflows/ci.yml", f"    - uses: actions/checkout@{SHA}\n", None),
        (".python-version", "3.14\n", "exact X.Y.Z"),
    ],
)
def test_pin_rules(tmp_path: Path, path: str, content: str, expected: str | None) -> None:
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    found = violations(tmp_path)
    if expected is None:
        assert found == []
    else:
        assert any(expected in v for v in found), found


@pytest.mark.parametrize(
    ("deps", "ok"),
    [
        (["fastapi==0.143.3", "psycopg[binary]==3.3.6"], True),
        (["fastapi>=0.143"], False),
        (["fastapi"], False),
        (["fastapi~=0.143.3"], False),
    ],
)
def test_python_requirements(tmp_path: Path, deps: list[str], ok: bool) -> None:
    listed = ", ".join(f'"{d}"' for d in deps)
    (tmp_path / "pyproject.toml").write_text(f"[project]\nname='x'\ndependencies=[{listed}]\n")
    (tmp_path / "uv.lock").write_text("")
    assert (violations(tmp_path) == []) is ok


@pytest.mark.parametrize(
    ("version", "ok"),
    [("1.2.3", True), ("workspace:*", True), ("^1.2.3", False), ("latest", False), ("~1.2", False)],
)
def test_node_dependencies(tmp_path: Path, version: str, ok: bool) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"x": version}}))
    (tmp_path / "pnpm-lock.yaml").write_text("")
    assert (violations(tmp_path) == []) is ok
