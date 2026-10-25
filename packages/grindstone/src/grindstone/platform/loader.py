"""The factory loader: validate every manifest before any factory code runs (SPEC-03).

1. Discover factories through the entry-point group `grindstone.factories` and
   read their files through `importlib.metadata`, which imports nothing.
2. Parse `manifest.yaml` with the safe YAML loader into `FactoryManifest`.
3. Phase 1, each factory alone: namespaces, SDK range, kinds, edges,
   lifecycles, capability files, check-method shapes, templates' own shape.
4. Phase 2, across factories, to a fixed point: references to other kinds,
   offered and requested needs, make and prove. Each pass checks the same
   union, so the result never depends on names or load order (REQ-0318).
5. Import each accepted factory's code module, check the adapters it names,
   compile its kinds and register all of its names in one step; then freeze.

A refused factory registers nothing and is reported with the file, field and
rule that failed; the kernel and every other factory still load (REQ-0304).
"""

import importlib
import json
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, field
from importlib.metadata import PackagePath, entry_points
from pathlib import Path
from typing import Any, cast, override

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from pydantic import ValidationError

from grindstone.contracts.base import Contract
from grindstone.contracts.hashing import hash_bytes, semantic_hash
from grindstone.contracts.platform import (
    CapabilityDecl,
    CheckShape,
    DeliverStep,
    EdgeDecl,
    FactoryManifest,
    FieldDecl,
    FieldType,
    KindDecl,
    OfferMode,
    TaskMode,
    TaskStep,
)
from grindstone.contracts.refs import SemanticHash
from grindstone.platform.kinds import compile_kind, kind_problems
from grindstone.platform.registries import (
    CORE,
    SDK_VERSION,
    Category,
    Origin,
    Registries,
    loading,
)
from grindstone.store.uow import Uow

ENTRY_POINT_GROUP = "grindstone.factories"
MANIFEST = "manifest.yaml"

MODE_OFFERS: Mapping[TaskMode, OfferMode] = {
    TaskMode.WORK: OfferMode.DELEGATE,
    TaskMode.CONSULT: OfferMode.CONSULT,
    TaskMode.CHECK: OfferMode.CHECK,
}
"""A task's mode and an offer's mode map one to one (SPEC-03, "Modes")."""

MAKER_MODES = frozenset({OfferMode.DELEGATE, OfferMode.CONSULT})

MECHANICAL_SHAPES = frozenset(
    {CheckShape.COMMAND, CheckShape.TEST, CheckShape.REPRODUCE, CheckShape.CROSS_TOOL}
)
"""Shapes a check station runs; `review` and `manual` are performed by capabilities or people."""


@dataclass(frozen=True, slots=True)
class Problem:
    """One refusal reason: the file, the field and the rule that failed."""

    factory: str
    file: str
    field: str
    rule: str
    code: str = "manifest_invalid"

    @override
    def __str__(self) -> str:
        return f"{self.file}:{self.field}: {self.rule}"


@dataclass(frozen=True, slots=True)
class FactorySource:
    """Where a factory's files are, readable without importing it."""

    name: str
    """The entry point's name, which must equal the manifest's namespace."""
    module: str
    """The importable package, imported only after the manifest passes."""
    read: Callable[[str], bytes | None]
    """A file's bytes by path relative to the package, or None if absent."""

    @classmethod
    def from_directory(cls, name: str, module: str, directory: Path) -> FactorySource:
        """A source whose files are a directory, such as a test fixture."""

        def read(relative: str) -> bytes | None:
            path = directory / relative
            return path.read_bytes() if path.is_file() else None

        return cls(name, module, read)


def discover() -> list[FactorySource]:
    """Every factory installed under the entry-point group, by name."""
    sources: list[FactorySource] = []
    for ep in sorted(entry_points(group=ENTRY_POINT_GROUP), key=lambda e: e.name):
        module = ep.value.partition(":")[0]
        prefix = module.replace(".", "/") + "/"
        index: dict[str, PackagePath] = {}
        for path in (ep.dist.files if ep.dist else None) or ():
            posix = path.as_posix()
            if posix.startswith(prefix):
                index[posix.removeprefix(prefix)] = path

        def read(relative: str, index: dict[str, PackagePath] = index) -> bytes | None:
            path = index.get(relative)
            return path.read_binary() if path is not None else None

        sources.append(FactorySource(ep.name, module, read))
    return sources


@dataclass(frozen=True, slots=True)
class LoadedFactory:
    """A factory whose names are registered."""

    name: str
    version: str
    manifest_hash: SemanticHash
    manifest: FactoryManifest
    capabilities: Mapping[str, CapabilityDecl]
    capability_hashes: Mapping[str, SemanticHash]
    kinds: Mapping[str, type[Contract]]
    adapters: Mapping[str, object]
    config_schema: Mapping[str, Any] | None = None
    """The JSON Schema for this factory's project section; None accepts no section (OQ-0302)."""


@dataclass(frozen=True, slots=True)
class LoadReport:
    """The start-up report: what loaded, and every refusal with its reasons."""

    loaded: tuple[LoadedFactory, ...]
    refused: Mapping[str, tuple[Problem, ...]]

    def lines(self) -> list[str]:
        """One line per loaded factory and per refusal reason."""
        out = [f"loaded {f.name} {f.version} {f.manifest_hash}" for f in self.loaded]
        for name, problems in sorted(self.refused.items()):
            out.extend(f"refused {name}: {p}" for p in problems)
        return out


@dataclass(slots=True)
class _Candidate:
    source: FactorySource
    manifest: FactoryManifest | None = None
    capabilities: dict[str, CapabilityDecl] = field(default_factory=dict[str, CapabilityDecl])
    capability_hashes: dict[str, SemanticHash] = field(default_factory=dict[str, SemanticHash])
    config_schema: dict[str, Any] | None = None
    problems: list[Problem] = field(default_factory=list[Problem])

    @property
    def name(self) -> str:
        return self.source.name

    @property
    def valid(self) -> FactoryManifest:
        """The manifest, for candidates that passed parsing; phase 2 sees only those."""
        if self.manifest is None:
            raise RuntimeError(f"{self.name}: no validated manifest")
        return self.manifest

    def refuse(self, file: str, where: str, rule: str, code: str = "manifest_invalid") -> None:
        self.problems.append(Problem(self.name, file, where, rule, code))


def load_factories(
    registries: Registries, sources: Iterable[FactorySource], *, sdk_version: str = SDK_VERSION
) -> LoadReport:
    """Load every source into `registries`, which hold the `core` names, then freeze them."""
    candidates = [_Candidate(s) for s in sources]
    _refuse_shared_namespaces(candidates)
    for candidate in candidates:
        if not candidate.problems:
            _phase_one(candidate, sdk_version)
    refused = {c.name: c for c in candidates if c.problems}
    accepted = sorted((c for c in candidates if not c.problems), key=lambda c: c.name)

    adapters: dict[str, dict[str, object]] = {}
    while True:
        accepted, newly = _phase_two(registries, accepted)
        refused.update({c.name: c for c in newly})
        newly = [c for c in accepted if c.name not in adapters and not _import_code(c, adapters)]
        if not newly:
            break
        refused.update({c.name: c for c in newly})
        accepted = [c for c in accepted if c.name not in refused]

    loaded = _register(registries, accepted, adapters)
    registries.freeze()
    return LoadReport(
        loaded=tuple(loaded),
        refused={n: tuple(c.problems) for n, c in sorted(refused.items())},
    )


def _refuse_shared_namespaces(candidates: list[_Candidate]) -> None:
    seen: dict[str, int] = {}
    for c in candidates:
        seen[c.name] = seen.get(c.name, 0) + 1
    for c in candidates:
        if seen[c.name] > 1:
            c.refuse(MANIFEST, "name", f"{seen[c.name]} installed factories claim this namespace")
        if c.name == CORE:
            c.refuse(MANIFEST, "name", "only the kernel registers the core namespace (I-18)")


# Phase 1: each factory alone.


def _phase_one(c: _Candidate, sdk_version: str) -> None:
    raw = _read_yaml(c, MANIFEST)
    if raw is None:
        return
    manifest = _validate(c, MANIFEST, FactoryManifest, raw)
    if manifest is None:
        return
    c.manifest = manifest
    ns = manifest.name
    if ns != c.name:
        c.refuse(MANIFEST, "name", f"{ns!r} differs from the entry point's name {c.name!r}")
        return
    try:
        if not SpecifierSet(manifest.sdk).contains(Version(sdk_version)):
            c.refuse(MANIFEST, "sdk", f"{manifest.sdk!r} does not admit SDK {sdk_version}")
    except InvalidSpecifier, InvalidVersion:
        c.refuse(MANIFEST, "sdk", f"{manifest.sdk!r} is not a PEP 440 specifier set")

    names: dict[str, list[tuple[str, str]]] = {
        "kinds": [(f"kinds[{i}].name", k.name) for i, k in enumerate(manifest.kinds)],
        "edges": [(f"edges[{i}].name", e.name) for i, e in enumerate(manifest.edges)]
        + [(f"edges[{i}].inverse", e.inverse) for i, e in enumerate(manifest.edges)],
        "templates": [(f"templates[{i}].name", t.name) for i, t in enumerate(manifest.templates)],
        "check_methods": [
            (f"check_methods[{i}].name", m.name) for i, m in enumerate(manifest.check_methods)
        ],
        "workspace_providers": _listed("workspace_providers", manifest.workspace_providers),
        "delivery_adapters": _listed("delivery_adapters", manifest.delivery_adapters),
        "decision_kinds": _listed("decision_kinds", manifest.decision_kinds),
        "secrets": _listed("secrets", manifest.secrets),
    }
    for group in names.values():
        _own_names(c, MANIFEST, ns, group)

    for i, kind in enumerate(manifest.kinds):
        for rule in kind_problems(kind):
            where, _, text = rule.partition(": ")
            c.refuse(MANIFEST, f"kinds[{i}].{where}", text)
    for i, template in enumerate(manifest.templates):
        _template_shape(c, i, template.steps)
    for i, path in enumerate(manifest.capabilities):
        _capability(c, ns, f"capabilities[{i}]", path)
    if manifest.config_schema is not None:
        _config_schema(c, manifest.config_schema)


def _listed(group: str, values: tuple[str, ...]) -> list[tuple[str, str]]:
    return [(f"{group}[{i}]", v) for i, v in enumerate(values)]


def _own_names(c: _Candidate, file: str, ns: str, named: list[tuple[str, str]]) -> None:
    seen: set[str] = set()
    for where, name in named:
        if name.startswith(f"{CORE}."):
            c.refuse(file, where, f"{name!r}: only the kernel registers core names (I-18)")
        elif not name.startswith(f"{ns}."):
            c.refuse(file, where, f"{name!r} is not in the {ns} namespace (I-18)")
        if name in seen:
            c.refuse(file, where, f"{name!r} is declared twice", "name_conflict")
        seen.add(name)


def _template_shape(c: _Candidate, index: int, steps: tuple[TaskStep | DeliverStep, ...]) -> None:
    earlier: set[str] = set()
    for j, step in enumerate(steps):
        where = f"templates[{index}].steps[{j}]"
        if step.name in earlier or any(s.name == step.name for s in steps[:j]):
            c.refuse(MANIFEST, f"{where}.name", f"step {step.name!r} is named twice")
        if isinstance(step, DeliverStep):
            source = next((s for s in steps[:j] if s.name == step.source), None)
            if not isinstance(source, TaskStep):
                c.refuse(MANIFEST, f"{where}.from", f"{step.source!r} is not an earlier task step")
        earlier.add(step.name)


def _capability(c: _Candidate, ns: str, where: str, path: str) -> None:
    raw = _read_yaml(c, path)
    if raw is None:
        return
    decl = _validate(c, path, CapabilityDecl, raw)
    if decl is None:
        return
    _own_names(c, path, ns, [("id", decl.id)])
    files = _capability_files(c, path, decl)
    for i, start in enumerate(decl.skills.start):
        if start not in decl.skills.library:
            c.refuse(path, f"skills.start[{i}]", f"{start!r} is not in the skill library")
    if decl.workspace.mode == "write":
        if decl.may_check:
            c.refuse(path, "may_check", "a capability with a writing workspace cannot prove")
        if decl.workspace.provider is None:
            c.refuse(path, "workspace.provider", "a writing workspace names its provider")
    if decl.permissions.otherwise == "decision":
        c.refuse(
            path,
            "permissions.otherwise",
            "`decision` waits for permission decisions with expiry (SPEC-15); use `deny` in M1",
        )
    for i, offer in enumerate(decl.offers):
        if not offer.need.startswith((f"{ns}.", f"{CORE}.")):
            c.refuse(path, f"offers[{i}].need", f"{offer.need!r} belongs to another factory")
    if decl.id in c.capabilities:
        c.refuse(path, "id", f"{decl.id!r} is declared twice", "name_conflict")
        return
    c.capabilities[decl.id] = decl
    c.capability_hashes[decl.id] = capability_hash(decl, files)


def _capability_files(c: _Candidate, path: str, decl: CapabilityDecl) -> dict[str, SemanticHash]:
    """Check the files a capability names exist, its report schemas are valid; hash them."""
    files: dict[str, SemanticHash] = {}
    for label, relative in (
        [("prompt", decl.prompt)]
        + [(f"skills.library[{i}]", s) for i, s in enumerate(decl.skills.library)]
        + [(f"produces.reports[{i}]", r) for i, r in enumerate(decl.produces.reports)]
    ):
        content = c.source.read(relative)
        if content is None:
            c.refuse(path, label, f"{relative!r} does not exist in the factory")
            continue
        files[relative] = _file_hash(content)
        if label.startswith("produces.reports"):
            _report_schema(c, path, label, relative, content)
    return files


def capability_hash(decl: CapabilityDecl, files: Mapping[str, str]) -> SemanticHash:
    """The capability's semantic hash with every file path replaced by its content hash."""
    hashed = decl.model_copy(
        update={
            "prompt": files.get(decl.prompt, decl.prompt),
            "skills": decl.skills.model_copy(
                update={
                    "library": tuple(files.get(s, s) for s in decl.skills.library),
                    "start": tuple(files.get(s, s) for s in decl.skills.start),
                }
            ),
            "produces": decl.produces.model_copy(
                update={"reports": tuple(files.get(r, r) for r in decl.produces.reports)}
            ),
        }
    )
    return semantic_hash(hashed)


def _file_hash(content: bytes) -> SemanticHash:
    """SHA-256 of a file's normalised bytes: text as NFC with LF line endings."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return hash_bytes(content)
    normal = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    return hash_bytes(normal.encode("utf-8"))


def _report_schema(c: _Candidate, file: str, where: str, relative: str, content: bytes) -> None:
    try:
        schema = json.loads(content)
        Draft202012Validator.check_schema(schema)
    except (ValueError, SchemaError) as exc:
        c.refuse(file, where, f"{relative!r} is not a valid JSON Schema: {_first_line(exc)}")


def _config_schema(c: _Candidate, relative: str) -> None:
    """The project-section schema exists and is a valid JSON Schema object (TKT-0303)."""
    content = c.source.read(relative)
    if content is None:
        c.refuse(MANIFEST, "config_schema", f"{relative!r} does not exist in the factory")
        return
    try:
        schema = json.loads(content)
        Draft202012Validator.check_schema(schema)
    except (ValueError, SchemaError) as exc:
        c.refuse(
            MANIFEST,
            "config_schema",
            f"{relative!r} is not a valid JSON Schema: {_first_line(exc)}",
        )
        return
    if not isinstance(schema, dict):
        c.refuse(MANIFEST, "config_schema", f"{relative!r} is not a JSON Schema object")
        return
    c.config_schema = cast(dict[str, Any], schema)


# Phase 2: across factories, to a fixed point.


@dataclass(slots=True)
class _Union:
    kinds: dict[str, KindDecl]
    edges: dict[str, EdgeDecl]
    shapes: dict[str, CheckShape]
    providers: set[str]
    adapters: set[str]
    capabilities: list[tuple[str, CapabilityDecl]]


def _union(registries: Registries, accepted: list[_Candidate]) -> _Union:
    u = _Union(
        kinds={
            n: cast(KindDecl, registries.require(Category.KIND, n).value)
            for n in registries.names(Category.KIND)
        },
        edges={
            n: cast(EdgeDecl, registries.require(Category.EDGE, n).value)
            for n in registries.names(Category.EDGE)
        },
        shapes={},
        providers=set(registries.names(Category.WORKSPACE_PROVIDER)),
        adapters=set(registries.names(Category.DELIVERY_ADAPTER)),
        capabilities=[],
    )
    for c in accepted:
        m = c.valid
        u.kinds.update({k.name: k for k in m.kinds})
        u.edges.update({e.name: e for e in m.edges})
        u.shapes.update({x.name: x.shape for x in m.check_methods})
        u.providers.update(m.workspace_providers)
        u.adapters.update(m.delivery_adapters)
        u.capabilities.extend((c.name, d) for d in c.capabilities.values())
    return u


def _phase_two(
    registries: Registries, accepted: list[_Candidate]
) -> tuple[list[_Candidate], list[_Candidate]]:
    """Refuse, pass after pass over the remaining union, until a pass refuses nothing."""
    refused: list[_Candidate] = []
    while True:
        union = _union(registries, accepted)
        failed = [c for c in accepted if _cross_factory_problems(c, union)]
        if not failed:
            return accepted, refused
        refused.extend(failed)
        accepted = [c for c in accepted if c not in failed]


def _cross_factory_problems(c: _Candidate, u: _Union) -> bool:
    m = c.valid
    before = len(c.problems)
    for i, kind in enumerate(m.kinds):
        for name, decl in kind.fields.items():
            _ref_rules(c, u, kind.name, f"kinds[{i}].fields.{name}", decl)
    for cap_id, decl in c.capabilities.items():
        provider = decl.workspace.provider
        if provider is not None and provider not in u.providers:
            c.refuse(cap_id, "workspace.provider", f"{provider!r} is not a registered provider")
    for i, template in enumerate(m.templates):
        for j, step in enumerate(template.steps):
            where = f"templates[{i}].steps[{j}]"
            if isinstance(step, DeliverStep):
                if step.adapter not in u.adapters:
                    c.refuse(MANIFEST, f"{where}.adapter", f"{step.adapter!r} is not registered")
                continue
            _task_step_rules(c, u, where, step)
    return len(c.problems) > before


def _ref_rules(c: _Candidate, u: _Union, kind: str, where: str, decl: FieldDecl) -> None:
    if decl.type is FieldType.LIST and decl.of is not None:
        _ref_rules(c, u, kind, f"{where}.of", decl.of)
        return
    if decl.type is not FieldType.REF:
        return
    own = {k.name for k in c.valid.kinds}
    for target in decl.kinds:
        if target not in own and not target.startswith(f"{CORE}."):
            c.refuse(
                MANIFEST,
                f"{where}.kinds",
                f"{target!r}: outside the namespace only core kinds (I-19)",
            )
        elif target not in u.kinds:
            c.refuse(MANIFEST, f"{where}.kinds", f"{target!r} is not a registered kind")
    edge = u.edges.get(decl.edge or "")
    if edge is None:
        c.refuse(MANIFEST, f"{where}.edge", f"{decl.edge!r} is not a registered edge")
        return
    if edge.from_kinds and kind not in edge.from_kinds:
        c.refuse(MANIFEST, f"{where}.edge", f"{edge.name!r} does not start at {kind!r}")
    if edge.to_kinds and (not decl.kinds or not set(decl.kinds) <= set(edge.to_kinds)):
        c.refuse(MANIFEST, f"{where}.edge", f"{edge.name!r} does not end at every target kind")


def _task_step_rules(c: _Candidate, u: _Union, where: str, step: TaskStep) -> None:
    mode = MODE_OFFERS[step.mode]
    makers = _offering(u, step.need, {mode} if mode is OfferMode.CHECK else MAKER_MODES)
    if not _offering(u, step.need, {mode}):
        c.refuse(
            MANIFEST, f"{where}.need", f"no loaded capability offers {step.need!r} as {mode.value}"
        )
    for k, check in enumerate(step.checks):
        at = f"{where}.checks[{k}]"
        shape = u.shapes.get(check.method)
        if shape is None:
            c.refuse(MANIFEST, f"{at}.method", f"{check.method!r} is not a registered check method")
            continue
        if shape is not CheckShape.REVIEW:
            continue  # mechanical checks run on the check station; manual ones by a person
        provers = _offering(u, check.by, {OfferMode.CHECK})
        if not provers:
            c.refuse(MANIFEST, f"{at}.by", f"no loaded capability offers {check.by!r} as check")
        for owner, decl in provers:
            if decl.workspace.mode == "write":
                c.refuse(MANIFEST, f"{at}.by", f"prover {owner}:{decl.id} has a writing workspace")
            if any(decl.id == maker.id for _, maker in makers):
                c.refuse(
                    MANIFEST,
                    f"{at}.by",
                    f"{owner}:{decl.id} offers both {step.need!r} and {check.by!r}: "
                    "a maker cannot prove its own work (I-15)",
                )


def _offering(
    u: _Union, need: str, modes: AbstractSet[OfferMode]
) -> list[tuple[str, CapabilityDecl]]:
    return [
        (owner, decl)
        for owner, decl in u.capabilities
        if any(o.need == need and modes & set(o.modes) for o in decl.offers)
    ]


# Code and registration.


def _import_code(c: _Candidate, adapters: dict[str, dict[str, object]]) -> bool:
    """Import a factory's code module, after its manifest passed; check what it names.

    Providers, adapters and mechanical check methods are code; review and
    manual checks are performed by capabilities or people, so a code-free
    factory stays valid (ADR-21).
    """
    m = c.valid
    mechanical = [x.name for x in m.check_methods if x.shape in MECHANICAL_SHAPES]
    named = (*m.workspace_providers, *m.delivery_adapters, *mechanical)
    if m.code is None:
        adapters[c.name] = {}
        if named:
            c.refuse(MANIFEST, "code", f"{', '.join(named)} need a code module")
            return False
        return True
    try:
        module = importlib.import_module(f"{c.source.module}.{m.code}")
    except Exception as exc:  # noqa: BLE001 - a factory's import error refuses that factory only
        c.refuse(
            MANIFEST,
            "code",
            f"importing {m.code!r} failed: {type(exc).__name__}",
            "factory_unavailable",
        )
        return False
    table = getattr(module, "ADAPTERS", None)
    if not isinstance(table, Mapping):
        c.refuse(MANIFEST, "code", f"{m.code!r} has no ADAPTERS mapping")
        return False
    found = cast(Mapping[str, object], table)
    missing = [n for n in named if n not in found]
    for name in missing:
        c.refuse(MANIFEST, "code", f"ADAPTERS has no {name!r}")
    # Port conformance joins with the port protocols (TKT-0607, SPEC-08).
    adapters[c.name] = dict(found)
    return not missing


def _register(
    registries: Registries, accepted: list[_Candidate], adapters: Mapping[str, Mapping[str, object]]
) -> list[LoadedFactory]:
    patterns = {
        n: cast(KindDecl, registries.require(Category.KIND, n).value).id.pattern
        for n in registries.names(Category.KIND)
    }
    for c in accepted:
        patterns.update({k.name: k.id.pattern for k in c.valid.kinds})
    loaded: list[LoadedFactory] = []
    for c in accepted:
        m = c.valid
        origin = Origin(m.name, m.version, semantic_hash(m))
        kinds = {k.name: compile_kind(k, patterns) for k in m.kinds}
        with loading(registries, origin):
            for k in m.kinds:
                registries.register(Category.KIND, k.name, k, origin)
            for e in m.edges:
                registries.register(Category.EDGE, e.name, e, origin)
            for need in sorted({o.need for d in c.capabilities.values() for o in d.offers}):
                if need.startswith(f"{m.name}."):
                    registries.register(Category.NEED, need, None, origin)
            for cap_id, decl in c.capabilities.items():
                registries.register(
                    Category.CAPABILITY,
                    cap_id,
                    decl,
                    origin,
                    capability_hash=c.capability_hashes[cap_id],
                )
            for t in m.templates:
                registries.register(Category.TEMPLATE, t.name, t, origin)
            for x in m.check_methods:
                registries.register(Category.CHECK_METHOD, x.name, x, origin)
            for name in m.workspace_providers:
                registries.register(
                    Category.WORKSPACE_PROVIDER, name, adapters[c.name].get(name), origin
                )
            for name in m.delivery_adapters:
                registries.register(
                    Category.DELIVERY_ADAPTER, name, adapters[c.name].get(name), origin
                )
            for name in m.decision_kinds:
                registries.register(Category.DECISION_KIND, name, None, origin)
        loaded.append(
            LoadedFactory(
                name=m.name,
                version=m.version,
                manifest_hash=origin.manifest_hash or semantic_hash(m),
                manifest=m,
                capabilities=dict(c.capabilities),
                capability_hashes=dict(c.capability_hashes),
                kinds=kinds,
                adapters=dict(adapters[c.name]),
                config_schema=c.config_schema,
            )
        )
    return loaded


# Parsing helpers.


def _read_yaml(c: _Candidate, path: str) -> object | None:
    content = c.source.read(path)
    if content is None:
        c.refuse(path, "-", "the file does not exist in the factory")
        return None
    try:
        return yaml.safe_load(content)
    except yaml.YAMLError as exc:
        c.refuse(path, "-", f"not safe YAML: {_first_line(exc)}")
        return None


def _validate[M: Contract](c: _Candidate, path: str, model: type[M], raw: object) -> M | None:
    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        for error in exc.errors():
            where = ".".join(str(p) for p in error["loc"]) or "-"
            c.refuse(path, where, error["msg"])
        return None


def _first_line(exc: Exception) -> str:
    return str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__


def report_rows(report: LoadReport) -> list[dict[str, Any]]:
    """The rows `platform.factories` records for one start, loaded and refused."""
    rows: list[dict[str, Any]] = [
        {
            "name": f.name,
            "version": f.version,
            "manifest_hash": f.manifest_hash,
            "status": "loaded",
            "report": json.dumps({"capabilities": dict(f.capability_hashes)}),
        }
        for f in report.loaded
    ]
    rows.extend(
        {
            "name": name,
            "version": None,
            "manifest_hash": None,
            "status": "refused",
            "report": json.dumps({"problems": [str(p) for p in problems]}),
        }
        for name, problems in report.refused.items()
    )
    return rows


def record_loads(uow: Uow, report: LoadReport) -> None:
    """Record one start's loads in `platform.factories`, a history (DEC-0304)."""
    for row in report_rows(report):
        uow.execute(
            "INSERT INTO platform.factories (name, version, manifest_hash, status, report)"
            " VALUES (:name, :version, :manifest_hash, :status, CAST(:report AS jsonb))",
            row,
        )
