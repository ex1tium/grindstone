"""SPEC-03, TKT-0302: the loader, kinds as data, capability hashing and load-time rules."""

import shutil
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from pydantic import ValidationError
from sqlalchemy import Engine, text

from grindstone.contracts.events import INSTANCE_STREAM
from grindstone.contracts.hashing import semantic_hash
from grindstone.contracts.ids import ProjectId
from grindstone.contracts.platform import InstanceConfig
from grindstone.contracts.provenance import AuthorKind, Provenance
from grindstone.platform import Category, Registries, core_registries
from grindstone.platform.configuration import FactoryState, Platform, create_project
from grindstone.platform.events import events_after
from grindstone.platform.loader import (
    FactorySource,
    LoadReport,
    discover,
    load_factories,
    record_loads,
)
from grindstone.store import Database, unit_of_work

FIXTURE = Path(__file__).parents[1] / "fixtures" / "factories" / "notes_fixture"

type Doc = dict[str, Any]


def _copy(tmp: Path, name: str = "notes") -> Path:
    target = tmp / name
    shutil.copytree(FIXTURE, target)
    return target


def _edit(path: Path, change: Callable[[Doc], None]) -> None:
    doc = cast(Doc, yaml.safe_load(path.read_text(encoding="utf-8")))
    change(doc)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _load(*dirs: tuple[str, Path]) -> tuple[Registries, LoadReport]:
    registries = core_registries()
    sources = [FactorySource.from_directory(n, f"fixture_{n}", d) for n, d in dirs]
    return registries, load_factories(registries, sources)


def _refusals(report: LoadReport, factory: str = "notes") -> list[str]:
    return [str(p) for p in report.refused.get(factory, ())]


def _rename(doc: Doc, old: str, new: str) -> None:
    """Rewrite a fixture namespace throughout a parsed YAML document."""
    for key, value in list(doc.items()):
        doc[key] = yaml.safe_load(yaml.safe_dump(value).replace(f"{old}.", f"{new}."))


@pytest.fixture
def site(tmp_path: Path) -> Iterator[Path]:
    """A directory on sys.path where tests install fixture distributions."""
    root = tmp_path / "site"
    root.mkdir()
    sys.path.insert(0, str(root))
    before = set(sys.modules)
    try:
        yield root
    finally:
        sys.path.remove(str(root))
        for name in set(sys.modules) - before:
            if name.startswith("gsfix"):
                del sys.modules[name]


def _install(site: Path, name: str, manifest: str, marker: Path) -> None:
    """A distribution with an entry point, a manifest and an `__init__` writing `marker`."""
    package = site / name
    package.mkdir()
    (package / "__init__.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('imported')\n",
        encoding="utf-8",
    )
    (package / "adapters.py").write_text("ADAPTERS = {}\n", encoding="utf-8")
    (package / "manifest.yaml").write_text(manifest, encoding="utf-8")
    info = site / f"{name}-0.1.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: 0.1.0\n")
    (info / "entry_points.txt").write_text(f"[grindstone.factories]\n{name} = {name}\n")
    files = [f"{name}/__init__.py", f"{name}/adapters.py", f"{name}/manifest.yaml"]
    (info / "RECORD").write_text("".join(f"{f},,\n" for f in files))


def test_loader_discovers_and_parses_safely(site: Path, tmp_path: Path) -> None:
    good, bad = tmp_path / "good-imported", tmp_path / "bad-imported"
    _install(
        site,
        "gsfixgood",
        'name: gsfixgood\nversion: 0.1.0\nsdk: ">=0.1.0,<0.2.0"\ncode: adapters\n',
        good,
    )
    _install(
        site,
        "gsfixbad",
        "name: !!python/object/apply:os.getcwd []\n"
        "version: 0.1.0\nsdk: '>=0.1.0'\ncode: adapters\n",
        bad,
    )
    sources = [s for s in discover() if s.name.startswith("gsfix")]
    assert [s.name for s in sources] == ["gsfixbad", "gsfixgood"]
    assert not good.exists()
    assert not bad.exists()

    report = load_factories(core_registries(), sources)
    assert [f.name for f in report.loaded] == ["gsfixgood"]
    assert good.exists()  # imported only after its manifest passed
    assert not bad.exists()  # never imported
    assert any("not safe YAML" in str(p) for p in report.refused["gsfixbad"])


def test_loader_registers_all_or_nothing(tmp_path: Path) -> None:
    notes = _copy(tmp_path)

    def break_template(doc: Doc) -> None:
        doc["templates"][0]["steps"][0]["need"] = "notes.missing"

    _edit(notes / "manifest.yaml", break_template)
    registries, report = _load(("notes", notes))
    assert "notes" in report.refused
    for category in Category:
        assert not [n for n in registries.names(category) if n.startswith("notes.")], category


@pytest.mark.parametrize(
    ("file", "keys", "value", "where"),
    [
        ("manifest.yaml", ("kinds", 0, "name"), "other.note", "kinds[0].name"),
        ("capabilities/writer.yaml", ("id",), "beta.writer", "capabilities/writer.yaml:id"),
        ("capabilities/writer.yaml", ("offers", 0, "need"), "beta.write", "offers[0].need"),
        ("manifest.yaml", ("sdk",), ">=0.2.0", "manifest.yaml:sdk"),
    ],
)
def test_namespace_and_sdk_range_rules(
    tmp_path: Path, file: str, keys: tuple[str | int, ...], value: str, where: str
) -> None:
    notes = _copy(tmp_path)

    def change(doc: Doc) -> None:
        target: Any = doc
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value

    _edit(notes / file, change)
    _, report = _load(("notes", notes))
    assert any(where in line for line in _refusals(report)), _refusals(report)


def test_kinds_compile_to_contracts(tmp_path: Path) -> None:
    _, report = _load(("notes", FIXTURE))
    note = report.loaded[0].kinds["notes.note"]
    a = note.model_validate({"body": "Proof.", "summary": "one", "title": "A"})
    b = note.model_validate({"body": "Proof.", "summary": "two", "title": "B"})
    assert semantic_hash(a) == semantic_hash(b)
    assert semantic_hash(a) != semantic_hash(note.model_validate({"body": "Other."}))
    note.model_validate({"body": "x", "links": ["N-2"]})
    with pytest.raises(ValidationError):
        note.model_validate({"body": "x", "links": ["P-3"]})

    notes = _copy(tmp_path)
    _edit(
        notes / "manifest.yaml", lambda d: d["kinds"][0]["fields"].update(ratio={"type": "float"})
    )
    _, refused = _load(("notes", notes))
    assert any("kinds.0.fields.ratio.type" in line for line in _refusals(refused))


def test_capability_validation_and_hash(tmp_path: Path) -> None:
    _, base = _load(("notes", FIXTURE))
    notes = _copy(tmp_path)
    prompt = notes / "prompts" / "writer.md"
    prompt.write_bytes(prompt.read_bytes() + b"!")
    _, changed = _load(("notes", notes))
    assert (
        changed.loaded[0].capability_hashes["notes.writer"]
        != base.loaded[0].capability_hashes["notes.writer"]
    )
    assert (
        changed.loaded[0].capability_hashes["notes.reviewer"]
        == base.loaded[0].capability_hashes["notes.reviewer"]
    )

    def writer_proves(doc: Doc) -> None:
        doc["workspace"] = {"mode": "write", "provider": "notes.files"}
        doc["may_check"] = [{"method": "notes.read_review"}]

    notes = _copy(tmp_path / "w")
    _edit(notes / "capabilities" / "writer.yaml", writer_proves)
    _, report = _load(("notes", notes))
    assert any("writing workspace cannot prove" in line for line in _refusals(report))

    notes = _copy(tmp_path / "s")
    (notes / "reports" / "review.json").write_text('{"type": 12}', encoding="utf-8")
    _, report = _load(("notes", notes))
    assert any("not a valid JSON Schema" in line for line in _refusals(report))


def test_load_refuses_maker_as_prover(tmp_path: Path) -> None:
    notes = _copy(tmp_path)
    _edit(
        notes / "capabilities" / "writer.yaml",
        lambda d: d["offers"].append({"need": "notes.review", "modes": ["check"]}),
    )
    _, report = _load(("notes", notes))
    lines = _refusals(report)
    assert any(
        "templates[0].steps[0].checks[0].by" in line and "notes:notes.writer" in line
        for line in lines
    )
    assert all(p.code == "manifest_invalid" for p in report.refused["notes"])


def test_load_accepts_separate_prover() -> None:
    registries, report = _load(("notes", FIXTURE))
    assert not report.refused
    assert registries.require(Category.TEMPLATE, "notes.write").origin.factory == "notes"
    assert set(registries.names(Category.NEED)) >= {"notes.write", "notes.review"}


def test_template_steps_validated(tmp_path: Path) -> None:
    notes = _copy(tmp_path)
    _edit(
        notes / "manifest.yaml", lambda d: d["templates"][0]["steps"][0].update(need="notes.nobody")
    )
    _, report = _load(("notes", notes))
    assert any("no loaded capability offers 'notes.nobody'" in line for line in _refusals(report))

    notes = _copy(tmp_path / "f")
    _edit(notes / "manifest.yaml", lambda d: d["templates"][0]["steps"][0].update(type="fan_out"))
    _, report = _load(("notes", notes))
    assert any("templates.0.steps.0" in line for line in _refusals(report))


@pytest.mark.parametrize("shape", ["magic", ["review", "test"]])
def test_check_methods_map_to_one_shape(tmp_path: Path, shape: object) -> None:
    notes = _copy(tmp_path)
    _edit(notes / "manifest.yaml", lambda d: d["check_methods"][0].update(shape=shape))
    _, report = _load(("notes", notes))
    assert any("check_methods.0.shape" in line for line in _refusals(report))


def _factory(tmp: Path, name: str, change: Callable[[Path], None]) -> Path:
    """A copy of the fixture renamed to namespace `name`, then changed."""
    target = _copy(tmp, name)
    for path in [target / "manifest.yaml", *(target / "capabilities").glob("*.yaml")]:
        _edit(path, lambda d: _rename(d, "notes", name))
    _edit(target / "manifest.yaml", lambda d: d.update(name=name))
    change(target)
    return target


def test_load_rules_independent_of_order(tmp_path: Path) -> None:
    # alpha's template asks core.advise for the work and core.review.impact for the
    # check; beta's one capability offers both, so alpha's maker could prove itself.
    def alpha_uses_core(d: Path) -> None:
        def change(doc: Doc) -> None:
            step = doc["templates"][0]["steps"][0]
            step.update(need="core.advise", mode="consult")
            step["checks"][0]["by"] = "core.review.impact"

        _edit(d / "manifest.yaml", change)

    def beta_offers_both(d: Path) -> None:
        _edit(
            d / "capabilities" / "writer.yaml",
            lambda doc: doc["offers"].extend(
                [
                    {"need": "core.advise", "modes": ["consult"]},
                    {"need": "core.review.impact", "modes": ["check"]},
                ]
            ),
        )

    alpha = _factory(tmp_path, "alpha", alpha_uses_core)
    beta = _factory(tmp_path, "beta", beta_offers_both)
    outcomes: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    for order in ([("alpha", alpha), ("beta", beta)], [("beta", beta), ("alpha", alpha)]):
        _, report = _load(*order)
        outcomes.add((tuple(f.name for f in report.loaded), tuple(report.refused)))
    assert outcomes == {(("beta",), ("alpha",))}

    # gamma's check is by a need only delta offers; delta fails on its own template,
    # so gamma falls in the next pass.
    def delta_broken(d: Path) -> None:
        _edit(
            d / "manifest.yaml",
            lambda doc: doc["templates"][0]["steps"][0].update(need="delta.nobody"),
        )

    def gamma_needs_delta(d: Path) -> None:
        _edit(
            d / "manifest.yaml",
            lambda doc: doc["templates"][0]["steps"][0]["checks"][0].update(by="delta.review"),
        )

    delta = _factory(tmp_path / "x", "delta", delta_broken)
    gamma = _factory(tmp_path / "y", "gamma", gamma_needs_delta)
    _, report = _load(("gamma", gamma), ("delta", delta))
    assert set(report.refused) == {"gamma", "delta"}
    assert any("delta.review" in line for line in _refusals(report, "gamma"))


def test_refused_factory_does_not_stop_kernel(
    tmp_path: Path, store: Database, engine: Engine
) -> None:
    # Both factories load at an earlier start, when each project is configured.
    broken = _factory(tmp_path, "broken", lambda d: None)
    _, earlier = _load(("notes", FIXTURE), ("broken", broken))
    assert not earlier.refused
    configure = Platform(InstanceConfig(), earlier)
    operator = Provenance(author_kind=AuthorKind.PERSON, author="operator", reason="enable")
    projects: dict[str, ProjectId] = {}
    for ns in ("notes", "broken"):
        project = unit_of_work(lambda uow, ns=ns: create_project(uow, f"uses-{ns}"))
        toml = f'[project]\nname = "{ns}"\n[factories]\n{ns} = "0.1.0"\n'
        unit_of_work(
            lambda uow, p=project, t=toml: configure.set_project_config(uow, p, t, operator)
        )
        projects[ns] = project

    # At this start `broken` is refused: the kernel and `notes` still start.
    (broken / "prompts" / "writer.md").unlink()
    registries, report = _load(("notes", FIXTURE), ("broken", broken))
    assert [f.name for f in report.loaded] == ["notes"]
    assert any(
        line.startswith("refused broken: capabilities/writer.yaml:prompt:")
        for line in report.lines()
    )
    assert registries.frozen

    unit_of_work(lambda uow: record_loads(uow, report))
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT name, version, manifest_hash, status FROM platform.factories ORDER BY name"
            )
        ).all()
    loaded = report.loaded[0]
    assert [tuple(r) for r in rows] == [
        ("broken", None, None, "refused"),
        ("notes", loaded.version, loaded.manifest_hash, "loaded"),
    ]
    entry = registries.require(Category.CAPABILITY, "notes.writer")
    assert entry.origin.manifest_hash == rows[1].manifest_hash  # AC-0317-1, against the table
    assert entry.capability_hash == loaded.capability_hashes["notes.writer"]
    events = unit_of_work(lambda uow: events_after(uow, INSTANCE_STREAM, 0))
    assert [(e.type, e.payload["factory"]) for e in events] == [
        ("factory.loaded", "notes"),
        ("factory.refused", "broken"),
    ]

    # Pause is derived from configuration validity and this start's loads, never stored.
    platform = Platform(InstanceConfig(), report)
    runs = unit_of_work(lambda uow: platform.project_status(uow, projects["notes"]))
    paused = unit_of_work(lambda uow: platform.project_status(uow, projects["broken"]))
    assert (runs.paused, dict(runs.factories)) == (False, {"notes": FactoryState.LOADED})
    assert (paused.paused, dict(paused.factories)) == (True, {"broken": FactoryState.REFUSED})
    assert [p.field for p in paused.problems] == ["factories.broken"]
    assert "refused at load" in paused.problems[0].rule
