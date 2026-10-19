"""FF-13: every cited identifier exists and the trace chain is complete."""

import shutil
from pathlib import Path

from scripts.ff.traceability import violations

from tests.fitness.helpers import FIXTURES, REPO


def _foundation_copy(tmp_path: Path) -> Path:
    shutil.copytree(REPO / "docs" / "foundation", tmp_path / "docs" / "foundation")
    return tmp_path


def test_repository_traces_cleanly() -> None:
    assert violations(REPO) == []


def test_dangling_id_fixture_fails_the_build(tmp_path: Path) -> None:
    root = _foundation_copy(tmp_path)
    shutil.copytree(FIXTURES / "dangling_id" / "docs" / "specs", root / "docs" / "specs")
    assert violations(root) == ["docs/specs/notes.md:3: cites undefined identifier ADR-99"]


def test_exit_criterion_without_a_specification_fails(tmp_path: Path) -> None:
    root = _foundation_copy(tmp_path)
    foundation = root / "docs" / "foundation" / "grindstone-foundation.md"
    text = foundation.read_text(encoding="utf-8")
    row = "| M1-04 | ADR-02"
    assert row in text
    foundation.write_text(text.replace(row, "|  | ADR-02", 1), encoding="utf-8")
    assert "spec map: exit criterion M1-04 is delivered by no specification" in violations(root)


def test_specification_citing_a_superseded_record_fails(tmp_path: Path) -> None:
    root = _foundation_copy(tmp_path)
    (root / "docs" / "specs").mkdir()
    (root / "docs" / "specs" / "SPEC-17-limits.md").write_text(
        "# SPEC-17 — Limits\nStatus: draft · Milestone: M3\n\nImplements: ADR-20.\n",
        encoding="utf-8",
    )
    assert violations(root) == ["docs/specs/SPEC-17-limits.md: cites superseded ADR-20"]


def test_implemented_specification_needs_a_test_per_criterion(tmp_path: Path) -> None:
    root = _foundation_copy(tmp_path)
    (root / "docs" / "specs").mkdir()
    (root / "docs" / "specs" / "SPEC-01-contracts.md").write_text(
        "# SPEC-01 — Contracts\nStatus: implemented · Milestone: M1\n\n"
        "AC-0101-1: hashes agree\nAC-0101-2: schemas generate\n",
        encoding="utf-8",
    )
    (root / "tests").mkdir()
    (root / "tests" / "test_contracts.py").write_text("# proves AC-0101-1\n", encoding="utf-8")
    assert violations(root) == ["docs/specs/SPEC-01-contracts.md: AC-0101-2 has no test naming it"]
