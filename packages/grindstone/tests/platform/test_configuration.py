"""SPEC-03, TKT-0303: instance and project configuration, `grindstone check`, secret grants."""

import hashlib
import inspect
import json
import logging
import secrets
import shutil
import typing
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from fastapi.testclient import TestClient

from grindstone import __main__ as cli
from grindstone import sdk
from grindstone.app import create_app
from grindstone.contracts.errors import ErrorClass
from grindstone.contracts.hashing import semantic_hash
from grindstone.contracts.ids import ProjectId, new_record_id
from grindstone.contracts.platform import InstanceConfig
from grindstone.contracts.provenance import AuthorKind, Provenance
from grindstone.platform import check as check_module
from grindstone.platform import core_registries
from grindstone.platform.configuration import (
    CONFIG_ENV,
    ConfigInvalidError,
    Platform,
    create_project,
    project_config,
    read_instance_config,
    startup_instance_config,
)
from grindstone.platform.loader import FactorySource, LoadReport, load_factories
from grindstone.platform.secrets import SecretNotGrantedError
from grindstone.store import Database, DatabaseSettings, unit_of_work

FIXTURE = Path(__file__).parents[1] / "fixtures" / "factories" / "notes_fixture"
DIGEST = "sha256:" + "0123456789abcdef" * 4

SCHEMA = {
    "type": "object",
    "properties": {
        "archive": {"type": "string"},
        "max_notes": {"type": "integer", "minimum": 1},
    },
    "additionalProperties": False,
}


def _notes(tmp: Path) -> Path:
    """The notes fixture with a project-section schema and two declared secrets."""
    target = tmp / "notes"
    shutil.copytree(FIXTURE, target)
    (target / "config.schema.json").write_text(json.dumps(SCHEMA), encoding="utf-8")
    manifest = target / "manifest.yaml"
    doc = cast(dict[str, Any], yaml.safe_load(manifest.read_text(encoding="utf-8")))
    doc.update(
        config_schema="config.schema.json", secrets=["notes.archive_token", "notes.other_token"]
    )
    manifest.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return target


def _sources(tmp: Path) -> list[FactorySource]:
    return [FactorySource.from_directory("notes", "fixture_notes", _notes(tmp))]


def _report(tmp: Path) -> LoadReport:
    report = load_factories(core_registries(), _sources(tmp))
    assert not report.refused, report.lines()
    return report


def _instance_toml(run_dir: str = "/run/gs") -> str:
    return f"""
[platform]
factories_allowed = ["notes"]

[images]
toolchain = "ghcr.io/example/toolchain:1@{DIGEST}"

[secrets]
postgres_password = '{run_dir}/postgres_password'
"notes.archive_token" = '{run_dir}/archive_token'
"notes.other_token" = '{run_dir}/other_token'
"notes.undeclared" = '{run_dir}/undeclared'

[surface]
cookie_secure = false
"""


PROJECT = """
[project]
name = "Notes"

[factories.notes]
version = "0.1.0"
archive = "s3://archive"
max_notes = 10

[grants]
secrets = ["notes.archive_token"]

[checks]
image = "toolchain"

[capabilities."notes.writer"]
effort = "high"
extra_prompt = "Write short notes."
"""


def test_instance_config_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    good = tmp_path / "grindstone.toml"
    good.write_text(_instance_toml(), encoding="utf-8")
    config = read_instance_config(good)
    assert config.images["toolchain"].endswith(DIGEST)
    assert config.secrets["notes.archive_token"] == "/run/gs/archive_token"  # noqa: S105 - a path
    assert semantic_hash(config) == semantic_hash(read_instance_config(good))

    inline = secrets.token_urlsafe(24)
    bad = tmp_path / "bad.toml"
    bad.write_text(
        _instance_toml()
        .replace("'/run/gs/archive_token'", f'"{inline}"')
        .replace(f":1@{DIGEST}", ":1"),
        encoding="utf-8",
    )
    with pytest.raises(ConfigInvalidError) as raised:
        read_instance_config(bad)
    fields = {(p.file, p.field) for p in raised.value.problems}
    assert fields == {(str(bad), 'secrets."notes.archive_token"'), (str(bad), "images.toolchain")}
    assert raised.value.envelope.code == "config_invalid"
    assert not any(inline in text for text in (str(raised.value), raised.value.envelope.message))

    floats = tmp_path / "floats.toml"
    floats.write_text("[limits]\nliveness_timeout = 1.5\n", encoding="utf-8")
    with pytest.raises(ConfigInvalidError) as raised:
        read_instance_config(floats)
    assert [p.field for p in raised.value.problems] == ["limits.liveness_timeout"]

    # Start-up stops on the invalid file, before it opens the database.
    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv(CONFIG_ENV, str(bad))
    with pytest.raises(ConfigInvalidError):
        startup_instance_config()
    unreachable = DatabaseSettings("127.0.0.1", 1, "x", "x", None)
    with pytest.raises(ConfigInvalidError), TestClient(create_app(unreachable)):
        pass
    assert any('secrets."notes.archive_token"' in r.getMessage() for r in caplog.records)
    assert not any(inline in r.getMessage() for r in caplog.records)

    monkeypatch.setenv(CONFIG_ENV, str(tmp_path / "missing.toml"))
    with pytest.raises(ConfigInvalidError) as raised:
        startup_instance_config()
    assert raised.value.problems[0].field == "-"


def read_instance_config_text(tmp: Path, text: str) -> InstanceConfig:
    path = tmp / "instance.toml"
    path.write_text(text, encoding="utf-8")
    return read_instance_config(path)


def _person(reason: str) -> Provenance:
    return Provenance(author_kind=AuthorKind.PERSON, author="operator", reason=reason)


def test_project_config_is_versioned_and_validated(tmp_path: Path, store: Database) -> None:
    platform = Platform(read_instance_config_text(tmp_path, _instance_toml()), _report(tmp_path))
    project = unit_of_work(lambda uow: create_project(uow, "notes-demo"))

    first = unit_of_work(
        lambda uow: platform.set_project_config(uow, project, PROJECT, _person("first"))
    )
    changed = PROJECT.replace("max_notes = 10", "max_notes = 20")
    second = unit_of_work(
        lambda uow: platform.set_project_config(uow, project, changed, _person("raise the cap"))
    )
    assert (first.version, second.version) == (1, 2)
    assert first.hash != second.hash
    assert (first.provenance.reason, second.provenance.reason) == ("first", "raise the cap")
    assert first.provenance.author_kind is AuthorKind.PERSON

    for toml, field in (
        (PROJECT.replace("max_notes = 10", "max_notes = 0"), "factories.notes.max_notes"),
        (PROJECT.replace("max_notes = 10", "colour = 1"), "factories.notes"),
        (PROJECT.replace('effort = "high"', 'prompt = "x"'), 'capabilities."notes.writer".prompt'),
        (PROJECT.replace('"toolchain"', '"other"'), "checks.image"),
        (PROJECT.replace('version = "0.1.0"', 'version = "0.2.0"'), "factories.notes.version"),
        (PROJECT.replace('["notes.archive_token"]', '["notes.nope"]'), "grants.secrets[0]"),
    ):
        with pytest.raises(ConfigInvalidError) as raised:
            unit_of_work(
                lambda uow, toml=toml: platform.set_project_config(
                    uow, project, toml, _person("bad")
                )
            )
        assert {p.field for p in raised.value.problems} == {field}

    current = unit_of_work(lambda uow: project_config(uow, project))
    assert current is not None
    assert (current.version, current.hash) == (2, second.hash)
    status = unit_of_work(lambda uow: platform.project_status(uow, project))
    assert not status.paused
    assert status.version == 2


def test_grindstone_check_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    sources = _sources(tmp_path)
    monkeypatch.setattr(check_module, "discover", lambda: sources)
    instance = tmp_path / "grindstone.toml"
    project = tmp_path / "notes.toml"
    instance.write_text(_instance_toml(), encoding="utf-8")
    project.write_text(PROJECT, encoding="utf-8")

    code = cli.main(["check", "--config", str(instance), "--project", str(project)])
    out = capsys.readouterr()
    assert (code, out.out) == (0, "")

    instance.write_text(
        _instance_toml().replace("'/run/gs/archive_token'", '"inline-value"'), encoding="utf-8"
    )
    project.write_text(
        PROJECT.replace("max_notes = 10", "max_notes = 0")
        .replace('version = "0.1.0"', 'version = "0.2.0"')
        .replace('"notes.writer"', '"notes.ghost"'),
        encoding="utf-8",
    )
    code = cli.main(["check", "--config", str(instance), "--project", str(project)])
    lines = capsys.readouterr().out.splitlines()
    assert code == 1
    assert [line.removeprefix(f"{instance}:").split(": ")[0] for line in lines[:1]] == [
        'secrets."notes.archive_token"'
    ]
    assert sorted(line.removeprefix(f"{project}:").split(": ")[0] for line in lines[1:]) == [
        'capabilities."notes.ghost"',
        "factories.notes.max_notes",
        "factories.notes.version",
    ]
    assert all(": " in line for line in lines)


def test_secret_grants(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    values: dict[str, str] = {}
    for name in ("archive_token", "other_token", "undeclared"):
        values[name] = secrets.token_urlsafe(32)
        (run_dir / name).write_text(values[name] + "\n", encoding="utf-8")
    instance = read_instance_config_text(tmp_path, _instance_toml(run_dir.as_posix()))
    platform = Platform(instance, _report(tmp_path))
    config, problems = platform.validate(PROJECT)
    assert config is not None
    assert not problems
    project = ProjectId(new_record_id())
    reader = platform.secrets_from(project, "notes", config)

    caplog.set_level(logging.DEBUG)
    value = reader.read("notes.archive_token")
    expected = hashlib.sha256(values["archive_token"].encode()).hexdigest()
    assert hashlib.sha256(value.encode()).hexdigest() == expected

    refusals: list[SecretNotGrantedError] = []
    for name in ("notes.other_token", "notes.undeclared", "beta.token", "postgres_password"):
        with pytest.raises(SecretNotGrantedError) as raised:
            reader.read(name)
        refusals.append(raised.value)
    for refusal in refusals:
        assert refusal.envelope.code == "secret_not_granted"
        assert refusal.envelope.error_class is ErrorClass.VALIDATION
        assert not refusal.envelope.retryable
    assert "does not grant" in str(refusals[0])
    assert "does not declare" in str(refusals[1])

    # A paused project grants nothing.
    with pytest.raises(SecretNotGrantedError):
        platform.secrets_from(project, "notes", None).read("notes.archive_token")

    texts = [r.getMessage() for r in caplog.records] + [str(r) for r in refusals]
    assert any("read secret notes.archive_token" in t for t in texts)
    assert not any(v in t for v in values.values() for t in texts)

    # The adapter passes only a name; the SDK offers no way to build a reader or context.
    assert list(inspect.signature(reader.read).parameters) == ["name"]
    assert typing.is_protocol(sdk.SecretReader)
    assert typing.is_protocol(sdk.Context)
    assert not {"Secrets", "Platform", "context_for"} & set(sdk.__all__)
