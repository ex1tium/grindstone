"""SPEC-09, TKT-0901: the `sdlc` manifest, its capabilities, template and schemas."""

import ast
import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from factories.sdlc.tests.support import (
    PACKAGE,
    Validator,
    load_sdlc,
    refused,
    selection,
    step_inputs,
    task_step,
)
from pydantic import JsonValue

from grindstone.contracts.platform import (
    CheckShape,
    DeliverStep,
    EdgeDecl,
    Impact,
    KindDecl,
    OfferMode,
)
from grindstone.platform import Category, Registries
from grindstone.platform.loader import LoadedFactory
from grindstone.platform.registries import SDK_VERSION

type Loaded = tuple[Registries, LoadedFactory]
type Doc = dict[str, Any]


def _variant(tmp_path: Path, file: str, change: Callable[[Doc], None]) -> Path:
    """A copy of the package with one YAML file changed."""
    target = tmp_path / "grindstone_sdlc"
    shutil.copytree(PACKAGE, target, ignore=shutil.ignore_patterns("__pycache__"))
    path = target / file
    doc = cast(Doc, yaml.safe_load(path.read_text(encoding="utf-8")))
    change(doc)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return target


def _kind(factory: LoadedFactory, name: str) -> KindDecl:
    return next(k for k in factory.manifest.kinds if k.name == name)


def _edge(factory: LoadedFactory, name: str) -> EdgeDecl:
    return next(e for e in factory.manifest.edges if e.name == name)


def _grindstone_imports(source: str) -> list[str]:
    """Every module under `grindstone` that a Python source imports."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append(node.module)
    return [m for m in found if m == "grindstone" or m.startswith("grindstone.")]


def test_sdlc_manifest_loads(loaded: Loaded) -> None:
    """AC-0901-1: loads with SDK 0.1.0, every name is `sdlc.`, imports only the SDK."""
    registries, factory = loaded
    assert SDK_VERSION == "0.1.0"
    assert (factory.name, factory.version) == ("sdlc", "0.1.0")

    names = [e.name for e in registries.entries() if e.origin.factory == "sdlc"]
    assert names
    assert all(n.startswith("sdlc.") for n in names), names
    inverses = [e.inverse for e in factory.manifest.edges]
    assert all(n.startswith("sdlc.") for n in inverses), inverses
    assert set(names) >= {
        "sdlc.requirement",
        "sdlc.criterion",
        "sdlc.ticket",
        "sdlc.verifies",
        "sdlc.implements",
        "sdlc.after",
        "sdlc.implementer",
        "sdlc.test_reviewer",
        "sdlc.implement",
        "sdlc.review.tests",
        "sdlc.ci_suite",
        "sdlc.git",
        "sdlc.github_pr",
    }

    modules = sorted(PACKAGE.rglob("*.py"))
    assert modules
    for module in modules:
        imports = _grindstone_imports(module.read_text(encoding="utf-8"))
        outside = [
            m for m in imports if m != "grindstone.sdk" and not m.startswith("grindstone.sdk.")
        ]
        assert not outside, f"{module.name} imports {outside} (FF-01: only grindstone.sdk)"


def test_sdlc_manifest_refused_outside_its_sdk_range() -> None:
    _, report = load_sdlc(sdk_version="0.2.0")
    assert any("does not admit SDK 0.2.0" in str(p) for p in report.refused["sdlc"])


def test_kinds_edges_and_lifecycles(loaded: Loaded) -> None:
    """REQ-0902 and REQ-0903, as the manifest declares them."""
    _, factory = loaded
    verifies = _edge(factory, "sdlc.verifies")
    assert (verifies.impact, verifies.check_dependency) == (Impact.REVIEW, True)
    assert (verifies.from_kinds, verifies.to_kinds) == (("sdlc.criterion",), ("sdlc.requirement",))
    implements = _edge(factory, "sdlc.implements")
    assert (implements.impact, implements.check_dependency) == (Impact.REVIEW, False)
    assert _edge(factory, "sdlc.after").check_dependency is False

    requirement = _kind(factory, "sdlc.requirement").lifecycle
    ticket = _kind(factory, "sdlc.ticket").lifecycle
    assert requirement is not None
    assert ticket is not None
    assert requirement.initial == "approved"
    assert ticket.initial == "ready"
    assert _kind(factory, "sdlc.criterion").lifecycle is None
    assert {(t.source, t.to, t.writer) for t in requirement.transitions} == {
        ("approved", "implemented", "task"),
        ("implemented", "verified", "evidence"),
        ("approved", "retired", "changeset"),
        ("implemented", "retired", "changeset"),
        ("verified", "retired", "changeset"),
    }
    assert ("in_review", "done", "delivery") in {
        (t.source, t.to, t.writer) for t in ticket.transitions
    }
    assert not any(t.source == "done" for t in ticket.transitions)

    criterion = factory.kinds["sdlc.criterion"]
    parsed = criterion.model_validate(
        {"title": "Slug", "condition": "c", "method": "test", "verifies": "REQ-0101"}
    )
    assert parsed.model_dump()["required"] is True
    with pytest.raises(ValueError, match="verifies"):
        criterion.model_validate({"condition": "c", "method": "test", "verifies": "TKT-0001"})


def test_reviewer_capability_shape(loaded: Loaded, tmp_path: Path) -> None:
    """AC-0906-1: the test reviewer is read-only, offers only `check`, may check only review
    on `git_commit`; a variant giving the implementer `sdlc.review.tests` is refused."""
    registries, factory = loaded
    reviewer = factory.capabilities["sdlc.test_reviewer"]
    assert reviewer.workspace.mode == "read_only"
    assert reviewer.workspace.provider is None
    assert [o.modes for o in reviewer.offers] == [(OfferMode.CHECK,)]
    assert [(m.method, m.subjects) for m in reviewer.may_check] == [
        ("sdlc.review", ("git_commit",))
    ]
    method = next(m for m in factory.manifest.check_methods if m.name == "sdlc.review")
    assert method.shape is CheckShape.REVIEW
    assert registries.get(Category.SUBJECT_KIND, "git_commit") is not None

    implementer = factory.capabilities["sdlc.implementer"]
    assert (implementer.workspace.mode, implementer.workspace.provider) == ("write", "sdlc.git")
    assert implementer.may_check == ()

    def give_review(doc: Doc) -> None:
        doc["offers"].append({"need": "sdlc.review.tests", "modes": ["check"]})

    _, report = load_sdlc(_variant(tmp_path, "capabilities/implementer.yaml", give_review))
    assert not report.loaded
    problems = [str(p) for p in report.refused["sdlc"]]
    assert any("a maker cannot prove its own work (I-15)" in p for p in problems), problems
    assert any("has a writing workspace" in p for p in problems), problems


def test_web_permission_only_on_implementer(loaded: Loaded) -> None:
    """AC-0906-2: `web` is the implementer's (ADR-55, ADR-57) and not the test reviewer's."""
    _, factory = loaded
    implementer = factory.capabilities["sdlc.implementer"].permissions
    reviewer = factory.capabilities["sdlc.test_reviewer"].permissions
    assert set(implementer.allow) == {"read", "write", "shell", "web"}
    assert set(reviewer.allow) == {"read", "shell"}
    assert implementer.otherwise == reviewer.otherwise == "deny"


def test_implement_refuses_uncheckable_criteria(loaded: Loaded) -> None:
    """AC-0904-2: `/implement` on a ticket with a `manual` criterion is refused, naming it.

    The template declares the refusal; the template runner applies it
    (SPEC-06 part 2, TKT-0601). Here the declared refusal is applied to
    criteria validated by the factory's compiled kind.
    """
    _, factory = loaded
    inputs = step_inputs(task_step(factory, "sdlc.implement", "implement"))
    criterion = factory.kinds["sdlc.criterion"]
    ticket = factory.kinds["sdlc.ticket"]

    def items(**methods: str) -> dict[str, tuple[str, dict[str, JsonValue]]]:
        found: dict[str, tuple[str, dict[str, JsonValue]]] = {
            "TKT-0001": (
                "sdlc.ticket",
                ticket.model_validate({"goal": "g", "implements": ["REQ-0101"]}).model_dump(
                    mode="json"
                ),
            )
        }
        for item, method in methods.items():
            fields = {"condition": "c", "method": method, "verifies": "REQ-0101"}
            found[item.replace("_", "-")] = (
                "sdlc.criterion",
                criterion.model_validate(fields).model_dump(mode="json"),
            )
        return found

    assert refused(inputs, items(AC_0101_1="test", AC_0101_2="manual")) == ["AC-0101-2"]
    assert refused(inputs, items(AC_0101_1="command")) == ["AC-0101-1"]
    assert refused(inputs, items(AC_0101_1="test", AC_0101_2="review")) == []


def test_implement_template_shape(loaded: Loaded) -> None:
    """REQ-0904 and REQ-0905, as the template declares them."""
    _, factory = loaded
    template = next(t for t in factory.manifest.templates if t.name == "sdlc.implement")
    assert template.command == "/implement"
    assert Validator(template.args).is_valid({"ticket": "TKT-0001"})
    assert not Validator(template.args).is_valid({"ticket": "REQ-0101"})

    step = task_step(factory, "sdlc.implement", "implement")
    inputs = step_inputs(step)
    assert inputs.start == "args.ticket"
    assert inputs.follow == (("sdlc.implements", False), ("sdlc.verifies", True))
    assert step.output in factory.capabilities["sdlc.implementer"].produces.reports

    ci, review = step.checks
    assert (ci.method, ci.by, ci.required) == ("sdlc.ci_suite", "station", True)
    assert [selection(t) for t in ci.targets] == [selection("sdlc.criterion[method=test]")]
    assert (review.method, review.by, review.required) == ("sdlc.review", "sdlc.review.tests", True)
    assert [selection(t) for t in review.targets] == [selection("sdlc.criterion")]

    deliver = template.steps[-1]
    assert isinstance(deliver, DeliverStep)
    assert (deliver.adapter, deliver.source) == ("sdlc.github_pr", "implement")


def test_report_schemas(loaded: Loaded) -> None:
    """The implementer's report and the test reviewer's `ReviewVerdict` (SPEC-08)."""
    _, factory = loaded
    implementer = factory.capabilities["sdlc.implementer"].produces.reports
    reviewer = factory.capabilities["sdlc.test_reviewer"].produces.reports
    assert implementer == ("schemas/implementation_report.json",)
    assert reviewer == ("schemas/test_review.json",)

    def validator(path: str) -> Validator:
        return Validator(json.loads((PACKAGE / path).read_text(encoding="utf-8")))

    report = validator(implementer[0])
    assert report.is_valid(
        {"summary": "Added slugify.", "criteria": ["AC-0101-1"], "tests": ["tests/test_text.py"]}
    )
    assert not report.is_valid({"summary": "Added slugify."})

    review = validator(reviewer[0])
    verdict: Doc = {
        "verdict": "fail",
        "targets": [
            {
                "item": "AC-0101-1",
                "verdict": "fail",
                "reason": "the diff deletes the assertion on '---'",
                "refs": ["tests/test_text.py"],
            }
        ],
        "acknowledgements": [{"key": "docs/notes.md", "verdict": "pass", "reason": "a note"}],
        "tests": [{"file": "tests/test_text.py", "name": "test_slugify", "note": "weakened"}],
    }
    assert review.is_valid(verdict)
    del verdict["targets"][0]["reason"]
    assert not review.is_valid(verdict)
    assert not review.is_valid({"verdict": "pass", "targets": []})


def test_prompts_carry_the_spec_instructions() -> None:
    implementer = (PACKAGE / "prompts" / "implementer.md").read_text(encoding="utf-8")
    reviewer = (PACKAGE / "prompts" / "test_reviewer.md").read_text(encoding="utf-8")
    assert "declared paths" in implementer
    assert "@verifies <criterion ID>" in implementer
    assert "call `report` once" in implementer
    assert "weakened or deleted" in reviewer
    assert '"diff truncated"' in reviewer
    assert "acknowledge" in reviewer


def test_config_schema(loaded: Loaded) -> None:
    """`[factories.sdlc]`, as the testbed's configuration will hold it."""
    _, factory = loaded
    assert factory.config_schema is not None
    schema = Validator(factory.config_schema)
    section: Doc = {
        "repository": "ex1tium/grindstone-testbed",
        "target_branch": "main",
        "app_id": 1,
        "installation_id": 2,
        "merge_method": "squash",
        "commands": {
            "gates": [{"name": "lint", "argv": ["ruff", "check", "."]}],
            "test": ["pytest", "--junitxml=$GRINDSTONE_OUT/junit.xml"],
        },
        "tests": {"glob": "tests/**/test_*.py", "def_pattern": r"^\s*def (test_\w+)\("},
        "toolchain": {"runtime": "python3.14", "package_manager": "uv", "lockfile": "uv.lock"},
        "paths": {"protected": ["deploy/**"], "reviewed": ["scripts/**"]},
        "published_paths": [".grindstone/**"],
        "diff_max_bytes": 1048576,
    }
    assert schema.errors(section) == []
    broken: list[Doc] = [
        {k: v for k, v in section.items() if k != "repository"},
        {**section, "merge_method": "fast-forward"},
        {**section, "token": "x"},
        {**section, "commands": {"test": []}},
    ]
    for doc in broken:
        assert not schema.is_valid(doc), doc
