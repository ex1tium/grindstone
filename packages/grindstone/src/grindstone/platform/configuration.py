"""Instance and project configuration, project status and secret grants (SPEC-03, TKT-0303).

- `grindstone.toml` is read with `tomllib` into `InstanceConfig`, its location
  from `GRINDSTONE_CONFIG`; an invalid file stops start-up with the file,
  field and rule of every error (REQ-0310).
- A project's configuration is a TOML document the control plane keeps as
  numbered versions with their hash and provenance. It is validated against
  the instance configuration and the loaded factories, each enabled factory's
  section against the schema that factory registered (REQ-0311). Only the
  operator's configuration command writes it (OQ-0301); no workspace, tool or
  report reaches it (I-14).
- `project_status` derives whether a project is paused from its current
  configuration's validity and the factory load status, read afresh each
  time and never stored (REQ-0304, REQ-0312, FF-09).
- `secrets` builds the reader a factory's adapter gets for one project
  (REQ-0315).
"""

import json
import logging
import os
import re
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, cast, override

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as SchemaViolation
from pydantic import ValidationError

from grindstone.contracts.base import Contract
from grindstone.contracts.errors import ErrorClass, ErrorEnvelope
from grindstone.contracts.hashing import HashInputError, semantic_hash
from grindstone.contracts.ids import ProjectId, new_record_id
from grindstone.contracts.platform import InstanceConfig, ProjectConfig
from grindstone.contracts.provenance import Provenance
from grindstone.contracts.refs import SemanticHash
from grindstone.platform.loader import LoadedFactory, LoadReport
from grindstone.platform.secrets import Secrets
from grindstone.store.uow import Uow

_log = logging.getLogger(__name__)

CONFIG_ENV = "GRINDSTONE_CONFIG"
DEFAULT_INSTANCE_CONFIG = Path("/etc/grindstone/grindstone.toml")
"""Mounted read-only in the control-plane container only (SPEC-05)."""


@dataclass(frozen=True, slots=True)
class ConfigProblem:
    """One configuration error: the file, the field and the rule that failed."""

    file: str
    field: str
    rule: str

    @override
    def __str__(self) -> str:
        return f"{self.file}:{self.field}: {self.rule}"


class ConfigInvalidError(Exception):
    """Configuration the rules refuse, with every problem and the `config_invalid` envelope."""

    def __init__(self, problems: Sequence[ConfigProblem]) -> None:
        self.problems = tuple(problems)
        message = "; ".join(str(p) for p in self.problems) or "invalid configuration"
        super().__init__(message)
        self.envelope = ErrorEnvelope(
            code="config_invalid",
            error_class=ErrorClass.VALIDATION,
            message=message,
            detail={"problems": [str(p) for p in self.problems]},
            retryable=False,
        )


# Field paths and parsing.

_BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


def _key(part: str) -> str:
    """A TOML key as written in a dotted path: bare when it can be, else quoted."""
    return part if _BARE_KEY.match(part) else json.dumps(part)


def _dotted(loc: Sequence[str | int]) -> str:
    out = ""
    for part in loc:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out = f"{out}.{_key(part)}" if out else _key(part)
    return out or "-"


def _parse_toml(file: str, text: str) -> tuple[dict[str, Any] | None, list[ConfigProblem]]:
    try:
        return tomllib.loads(text), []
    except tomllib.TOMLDecodeError as exc:
        return None, [ConfigProblem(file, "-", f"not valid TOML: {exc}")]


def _validate[M: Contract](
    file: str, model: type[M], raw: object
) -> tuple[M | None, list[ConfigProblem]]:
    try:
        config = model.model_validate(raw)
    except ValidationError as exc:
        problems: list[ConfigProblem] = []
        for error in exc.errors():
            loc = list(error["loc"])
            if len(loc) >= 3 and loc[0] == "factories" and loc[2] == "section":
                del loc[2]  # the factory's own keys sit beside `version` in TOML
            rule = error["msg"].removeprefix("Value error, ")
            problems.append(ConfigProblem(file, _dotted(loc), rule))
        return None, problems
    try:
        semantic_hash(config)
    except HashInputError as exc:
        pointer = str(exc.envelope.detail.get("pointer", ""))
        where = pointer.strip("/").replace("/", ".") or "-"
        return None, [ConfigProblem(file, where, exc.envelope.message)]
    return config, []


# Instance configuration.


def instance_config_path() -> Path:
    """`GRINDSTONE_CONFIG`, or the read-only mount the deployment provides."""
    configured = os.environ.get(CONFIG_ENV)
    return Path(configured) if configured else DEFAULT_INSTANCE_CONFIG


def check_instance_config(path: Path) -> tuple[InstanceConfig | None, tuple[ConfigProblem, ...]]:
    """The instance configuration in `path`, or None with every problem found."""
    file = str(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        reason = exc.strerror or type(exc).__name__
        return None, (ConfigProblem(file, "-", f"the file cannot be read: {reason}"),)
    raw, problems = _parse_toml(file, text)
    if raw is None:
        return None, tuple(problems)
    config, problems = _validate(file, InstanceConfig, raw)
    return config, tuple(problems)


def read_instance_config(path: Path | None = None) -> InstanceConfig:
    """The validated instance configuration, or `ConfigInvalidError` naming every error."""
    config, problems = check_instance_config(path or instance_config_path())
    if config is None:
        raise ConfigInvalidError(problems)
    return config


def startup_instance_config() -> InstanceConfig:
    """The instance configuration start-up uses; a missing or invalid file stops the process.

    The file is `GRINDSTONE_CONFIG`, else the default the Compose deployment
    mounts from `deploy/grindstone.toml` (SPEC-05).
    """
    path = instance_config_path()
    try:
        config = read_instance_config(path)
    except ConfigInvalidError as exc:
        for problem in exc.problems:
            _log.error("instance configuration invalid: %s", problem)
        raise
    _log.info("instance configuration %s %s", path, semantic_hash(config))
    return config


# Project configuration.


def _factory_entries(raw: dict[str, Any]) -> dict[str, Any]:
    """`[factories]` as `FactoryEntry` input: a version string, or a table with `version`."""
    factories = raw.get("factories")
    if not isinstance(factories, dict):
        return raw
    entries: dict[str, object] = {}
    for ns, value in cast(dict[str, object], factories).items():
        if isinstance(value, str):
            entries[ns] = {"version": value}
        elif isinstance(value, dict):
            table = dict(cast(dict[str, object], value))
            entry: dict[str, object] = {"section": table}
            if "version" in table:
                entry["version"] = table.pop("version")
            entries[ns] = entry
        else:
            entries[ns] = value
    return {**raw, "factories": entries}


def project_problems(
    config: ProjectConfig, file: str, report: LoadReport, instance: InstanceConfig | None
) -> list[ConfigProblem]:
    """The rules that span a project configuration, the instance and the loaded factories.

    Without a valid instance configuration only the factory rules apply.
    """
    loaded = {f.name: f for f in report.loaded}
    problems: list[ConfigProblem] = []

    def refuse(where: str, rule: str) -> None:
        problems.append(ConfigProblem(file, where, rule))

    allowed = instance.platform.factories_allowed if instance is not None else None
    for ns, entry in sorted(config.factories.items()):
        at = f"factories.{_key(ns)}"
        if allowed is not None and ns not in allowed:
            refuse(at, f"{ns!r} is not in the instance's [platform].factories_allowed")
        factory = loaded.get(ns)
        if factory is None:
            if ns in report.refused:
                refuse(at, f"factory {ns!r} was refused at load; see the start-up report")
            else:
                refuse(at, f"no factory {ns!r} is installed")
            continue
        if factory.version != entry.version:
            refuse(f"{at}.version", f"{ns} is loaded at {factory.version}, not {entry.version}")
        problems.extend(_section_problems(file, at, factory, entry.section))

    for i, name in enumerate(config.grants.secrets):
        for rule in _grant_problems(name, config, loaded, instance):
            refuse(f"grants.secrets[{i}]", rule)

    image = config.checks.image
    if image is not None and instance is not None and image not in instance.images:
        refuse("checks.image", f"{image!r} is not an image in the instance's [images]")

    enabled = {cap for ns in config.factories if ns in loaded for cap in loaded[ns].capabilities}
    for cap_id in sorted(config.capabilities):
        if cap_id not in enabled:
            refuse(
                f"capabilities.{_key(cap_id)}",
                f"{cap_id!r} is not a capability of a factory this project enables",
            )
    return problems


def _grant_problems(
    name: str,
    config: ProjectConfig,
    loaded: Mapping[str, LoadedFactory],
    instance: InstanceConfig | None,
) -> list[str]:
    """A secret grant names a secret its own, enabled factory declares (REQ-0315)."""
    ns, dot, _ = name.partition(".")
    if not dot:
        return [f"{name!r} is a kernel secret; a project grants only factory secrets"]
    if ns not in config.factories:
        return [f"{name!r} belongs to {ns!r}, which this project does not enable"]
    rules: list[str] = []
    factory = loaded.get(ns)
    if factory is not None and name not in factory.manifest.secrets:
        rules.append(f"{ns} declares no secret {name!r}")
    if instance is not None and name not in instance.secrets:
        rules.append(f"{name!r} has no file in the instance's [secrets]")
    return rules


def _section_problems(
    file: str, at: str, factory: LoadedFactory, section: Mapping[str, object]
) -> list[ConfigProblem]:
    """A factory's project section against the schema it registered (OQ-0302: optional)."""
    if factory.config_schema is None:
        if section:
            rule = f"{factory.name} registers no config_schema, so it accepts no section"
            return [ConfigProblem(file, at, rule)]
        return []
    validator = Draft202012Validator(factory.config_schema)
    errors = cast(Iterable[SchemaViolation], cast(Any, validator).iter_errors(dict(section)))
    problems: list[ConfigProblem] = []
    for error in sorted(errors, key=lambda e: [str(p) for p in e.absolute_path]):
        path = list(error.absolute_path)
        problems.append(ConfigProblem(file, f"{at}.{_dotted(path)}" if path else at, error.message))
    return problems


def validate_project(
    text: str, file: str, report: LoadReport, instance: InstanceConfig | None
) -> tuple[ProjectConfig | None, tuple[ConfigProblem, ...]]:
    """Parse and validate a project configuration; the config is None when it cannot be parsed."""
    raw, problems = _parse_toml(file, text)
    if raw is None:
        return None, tuple(problems)
    config, problems = _validate(file, ProjectConfig, _factory_entries(raw))
    if config is None:
        return None, tuple(problems)
    return config, tuple(project_problems(config, file, report, instance))


# Stored projects, configuration versions and status.


class FactoryState(StrEnum):
    """How a factory a project enables stands at this start."""

    LOADED = "loaded"
    REFUSED = "refused"
    ABSENT = "absent"


@dataclass(frozen=True, slots=True)
class ProjectConfigVersion:
    """One stored version of a project's configuration."""

    project: ProjectId
    version: int
    toml: str
    hash: SemanticHash
    provenance: Provenance
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ProjectStatus:
    """A project's configuration validity and its factories' load status, derived now."""

    project: ProjectId
    slug: str
    version: int | None
    problems: tuple[ConfigProblem, ...]
    factories: Mapping[str, FactoryState] = field(default_factory=dict[str, FactoryState])

    @property
    def paused(self) -> bool:
        """Paused while the current configuration is missing or invalid (REQ-0304, REQ-0312)."""
        return bool(self.problems)


def create_project(uow: Uow, slug: str) -> ProjectId:
    """Give a project its identity; it runs nothing until it has a valid configuration."""
    project = ProjectId(new_record_id())
    uow.execute(
        "INSERT INTO platform.projects (id, slug) VALUES (:id, :slug)",
        {"id": project, "slug": slug},
    )
    return project


def project_config(uow: Uow, project: ProjectId) -> ProjectConfigVersion | None:
    """The current, highest version of a project's configuration, if it has one."""
    row = uow.fetch_one(
        "SELECT version, toml, hash, provenance, created_at FROM platform.project_configs"
        " WHERE project = :project ORDER BY version DESC LIMIT 1",
        {"project": project},
    )
    if row is None:
        return None
    return ProjectConfigVersion(
        project=project,
        version=row["version"],
        toml=row["toml"],
        hash=row["hash"],
        provenance=Provenance.model_validate(row["provenance"]),
        created_at=row["created_at"],
    )


_LATEST = (
    "SELECT p.id, p.slug, c.version, c.toml FROM platform.projects p"
    " LEFT JOIN LATERAL (SELECT version, toml FROM platform.project_configs"
    " WHERE project = p.id ORDER BY version DESC LIMIT 1) c ON true"
)


def latest_project_configs(uow: Uow) -> list[tuple[ProjectId, str, int | None, str | None]]:
    """Every project with its current configuration version and text, by slug."""
    rows = uow.fetch_all(_LATEST + " ORDER BY p.slug")
    return [(ProjectId(r["id"]), r["slug"], r["version"], r["toml"]) for r in rows]


def stored_config_file(slug: str, version: int | None) -> str:
    """How errors name a stored configuration: `projects/<slug>@<version>`."""
    return f"projects/{slug}" if version is None else f"projects/{slug}@{version}"


@dataclass(frozen=True, slots=True)
class Platform:
    """The instance configuration and this start's factory loads, which project rules read."""

    instance: InstanceConfig
    report: LoadReport

    def validate(
        self, toml: str, file: str = "project.toml"
    ) -> tuple[ProjectConfig | None, tuple[ConfigProblem, ...]]:
        return validate_project(toml, file, self.report, self.instance)

    def set_project_config(
        self, uow: Uow, project: ProjectId, toml: str, provenance: Provenance
    ) -> ProjectConfigVersion:
        """Validate and store the next version; on any error nothing is stored (REQ-0311).

        TKT-0304 adds the `project.configured` event to this unit of work.
        """
        row = uow.fetch_one("SELECT slug FROM platform.projects WHERE id = :id", {"id": project})
        if row is None:
            raise KeyError(f"no project {project}")
        config, problems = self.validate(toml, stored_config_file(row["slug"], None))
        if config is None or problems:
            raise ConfigInvalidError(problems)
        uow.lock(f"platform.project_configs:{project}")
        current = project_config(uow, project)
        version = 1 if current is None else current.version + 1
        digest = semantic_hash(config)
        uow.execute(
            "INSERT INTO platform.project_configs (project, version, toml, hash, provenance)"
            " VALUES (:project, :version, :toml, :hash, CAST(:provenance AS jsonb))",
            {
                "project": project,
                "version": version,
                "toml": toml,
                "hash": digest,
                "provenance": provenance.model_dump_json(),
            },
        )
        stored = project_config(uow, project)
        if stored is None:  # pragma: no cover - inserted just above
            raise RuntimeError(f"{project}: configuration version {version} not stored")
        return stored

    def project_status(self, uow: Uow, project: ProjectId) -> ProjectStatus:
        """Whether a project is paused, from its configuration and the factory loads now."""
        row = uow.fetch_one(_LATEST + " WHERE p.id = :id", {"id": project})
        if row is None:
            raise KeyError(f"no project {project}")
        return self._status(project, row["slug"], row["version"], row["toml"])

    def project_statuses(self, uow: Uow) -> list[ProjectStatus]:
        """The status of every project, by slug."""
        return [self._status(*latest) for latest in latest_project_configs(uow)]

    def secrets(self, uow: Uow, project: ProjectId, factory: str) -> Secrets:
        """The secret reader kernel code puts in `factory`'s context for `project`.

        Grants come from the project's current configuration while it is
        valid; a paused project grants nothing.
        """
        current = project_config(uow, project)
        config: ProjectConfig | None = None
        if current is not None:
            parsed, problems = self.validate(current.toml)
            config = None if problems else parsed
        return self.secrets_from(project, factory, config)

    def secrets_from(
        self, project: ProjectId, factory: str, config: ProjectConfig | None
    ) -> Secrets:
        """The reader for `factory` in `project`, given that project's valid configuration."""
        loaded = next((f for f in self.report.loaded if f.name == factory), None)
        return Secrets(
            project=project,
            factory=factory,
            declared=frozenset(loaded.manifest.secrets if loaded is not None else ()),
            granted=frozenset(config.grants.secrets if config is not None else ()),
            files=self.instance.secrets,
        )

    def _status(
        self, project: ProjectId, slug: str, version: int | None, toml: str | None
    ) -> ProjectStatus:
        file = stored_config_file(slug, version)
        if version is None or toml is None:
            missing = (ConfigProblem(file, "-", "the project has no configuration"),)
            return ProjectStatus(project, slug, None, missing)
        config, problems = self.validate(toml, file)
        states: dict[str, FactoryState] = {}
        for ns in config.factories if config is not None else ():
            if any(f.name == ns for f in self.report.loaded):
                states[ns] = FactoryState.LOADED
            elif ns in self.report.refused:
                states[ns] = FactoryState.REFUSED
            else:
                states[ns] = FactoryState.ABSENT
        return ProjectStatus(project, slug, version, problems, states)
