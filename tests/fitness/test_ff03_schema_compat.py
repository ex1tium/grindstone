"""FF-03: a breaking schema change needs a version bump and an upgrade entry."""

import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from scripts.ff.schema_compat import BUNDLE, base_bundle, main, violations

from tests.fitness.helpers import REPO

HASHES = "**Stored hashes.**"


def _bundle() -> dict[str, Any]:
    return json.loads((REPO / BUNDLE).read_text(encoding="utf-8"))


def _model(bundle: dict[str, Any], name: str) -> dict[str, Any]:
    return bundle["$defs"][name]


def _bump(bundle: dict[str, Any], name: str, version: int) -> None:
    _model(bundle, name)["properties"]["schema_version"].update(const=version, default=version)


def _without_field(name: str, field: str) -> dict[str, Any]:
    head = _bundle()
    model = _model(head, name)
    del model["properties"][field]
    model["required"].remove(field)
    return head


def test_ff03_breaking_change_needs_version_bump() -> None:
    base = _bundle()
    removed = _without_field("BlobRef", "media_type")
    assert violations(base, removed, "") == [
        "BlobRef: field `media_type` removed; breaking without raising schema_version (still 1)"
    ]

    added = _bundle()
    _model(added, "BlobRef")["properties"]["label"] = {"default": None, "type": "string"}
    _model(added, "BlobRef")["required"].append("label")
    assert violations(base, added, "") == []

    _bump(removed, "BlobRef", 2)
    assert violations(base, removed, "") == [
        "BlobRef: field `media_type` removed; docs/upgrades.md has no `## BlobRef v2` entry"
    ]
    entry = "# Upgrades\n\n## BlobRef v2\n\n`media_type` is dropped on read.\n"
    assert violations(base, removed, entry) == []


def test_repository_bundle_is_compatible_with_itself() -> None:
    assert violations(_bundle(), _bundle(), "") == []


def test_no_base_bundle_means_every_model_is_new() -> None:
    assert violations(None, _bundle(), "") == []


def _new_enum_member(b: dict[str, Any]) -> None:
    _model(b, "AuthorKind")["enum"].append("robot")


def _new_inline_enum_member(b: dict[str, Any]) -> None:
    _model(b, "ServiceHealth")["properties"]["service"]["enum"].append("indexer")


def _new_description(b: dict[str, Any]) -> None:
    _model(b, "ServiceHealth")["description"] = "New words."


def _new_model(b: dict[str, Any]) -> None:
    b["$defs"]["NewThing"] = {"type": "object", "properties": {}}


def _narrowed_type(b: dict[str, Any]) -> None:
    _model(b, "BlobRef")["properties"]["size"]["minimum"] = 1


def _new_required_field(b: dict[str, Any]) -> None:
    _model(b, "BlobRef")["properties"]["extra"] = {"type": "string"}
    _model(b, "BlobRef")["required"].append("extra")


def _made_required(b: dict[str, Any]) -> None:
    del _model(b, "ServiceHealth")["properties"]["dependencies"]["default"]


def _default_changed(b: dict[str, Any]) -> None:
    _model(b, "Provenance")["properties"]["task"]["default"] = "x"


def _model_removed(b: dict[str, Any]) -> None:
    del b["$defs"]["GitCommitSubject"]


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (_new_enum_member, None),
        (_new_inline_enum_member, None),
        (_new_description, None),
        (_new_model, None),
        (_narrowed_type, "BlobRef: field `size` type changed"),
        (_new_required_field, "BlobRef: required field `extra` added"),
        (_made_required, "ServiceHealth: field `dependencies` made required"),
        (_default_changed, "Provenance: semantic field `task` default changed"),
        (_model_removed, "GitCommitSubject: model removed"),
    ],
)
def test_change_classification(
    change: Callable[[dict[str, Any]], None], expected: str | None
) -> None:
    head = _bundle()
    change(head)
    found = violations(_bundle(), head, "")
    if expected is None:
        assert found == []
    else:
        assert len(found) == 1
        assert found[0].startswith(expected), found


def test_removed_enum_member_is_charged_to_every_versioned_user() -> None:
    head = _bundle()
    _model(head, "HealthStatus")["enum"].remove("degraded")
    found = violations(_bundle(), head, "")
    assert [v.split(":")[0] for v in found] == ["ServiceHealth"]
    assert "`HealthStatus`: definition changed" in found[0]


def test_semantic_default_change_must_say_how_hashes_are_treated() -> None:
    head = _bundle()
    _model(head, "Provenance")["properties"]["task"]["default"] = "x"
    _bump(head, "Provenance", 2)
    entry = "## Provenance v2\n\n`task` defaults to x.\n"
    [found] = violations(_bundle(), head, entry)
    assert "must say how stored hashes are treated" in found
    assert violations(_bundle(), head, f"{entry}\n{HASHES} Recomputed on read.\n") == []


def test_removed_model_needs_a_removal_entry() -> None:
    head = _bundle()
    del head["$defs"]["GitCommitSubject"]
    found = violations(_bundle(), head, "## GitCommitSubject removed\n\nGone.\n")
    assert found == []


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_reads_the_base_bundle_from_git(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "ff03@example.invalid")
    _git(tmp_path, "config", "user.name", "FF-03")
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "empty")
    assert base_bundle(tmp_path, "main") is None
    with pytest.raises(LookupError):
        base_bundle(tmp_path, "no-such-ref")

    target = tmp_path / BUNDLE
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(_bundle()), encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "bundle")
    assert main(["ff03", "--base", "main", str(tmp_path)]) == 0

    target.write_text(json.dumps(_without_field("BlobRef", "size")), encoding="utf-8")
    assert main(["ff03", "--base", "main", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "FF-03 BlobRef: field `size` removed" in out
    assert out.rstrip().endswith("against main: 1 violation(s)")
