"""Factory manifests and configuration, as data (SPEC-03, ADR-21, ADR-23).

A manifest is validated before any of the factory's code runs. These models
fix its shape; the loader (TKT-0302) applies the rules that span fields and
factories: namespaces, references, make and prove, check shapes, templates.
Instance and project configuration follow (TKT-0303); the rules that span
them and the loaded factories are `grindstone.platform`'s.
"""

import re
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Literal

from pydantic import AfterValidator, Field, JsonValue

from grindstone.contracts.base import Contract


class FieldType(StrEnum):
    """The fixed vocabulary of item field types; no floats (SPEC-01, DEC-0102)."""

    STRING = "string"
    TEXT = "text"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ENUM = "enum"
    REF = "ref"
    BLOB = "blob"
    LIST = "list"


class Cardinality(StrEnum):
    ONE = "one"
    MANY = "many"


class FieldDecl(Contract):
    """One field of an item kind."""

    type: FieldType
    values: tuple[str, ...] = ()
    """For `enum`: the admitted values."""
    kinds: tuple[str, ...] = ()
    """For `ref`: the kinds it may target; empty means any kind."""
    edge: str | None = None
    """For `ref`: the edge type the reference creates."""
    cardinality: Cardinality = Cardinality.ONE
    of: FieldDecl | None = None
    """For `list`: the element type, one of the other types."""
    presentation: bool = False
    required: bool = True
    default: JsonValue = None


class IdDecl(Contract):
    """How a kind's IDs look: an anchored pattern, examples, and optionally an allocation format."""

    pattern: str
    examples: tuple[str, ...] = Field(min_length=1)
    allocate: str | None = None
    """For kernel-allocated IDs, a format such as `FND-{n}`."""


class Transition(Contract):
    source: str = Field(alias="from")
    to: str
    writer: str


class Lifecycle(Contract):
    states: tuple[str, ...] = Field(min_length=1)
    initial: str
    transitions: tuple[Transition, ...] = ()


class KindDecl(Contract):
    """An item kind, declared as data and compiled into a contract (DEC-0301)."""

    name: str
    id: IdDecl
    fields: dict[str, FieldDecl]
    lifecycle: Lifecycle | None = None


class Impact(StrEnum):
    """What a change at an edge's target does to its source (ADR-10)."""

    REVIEW = "review"
    NOTIFY = "notify"
    RENDER = "render"


class EdgeDecl(Contract):
    name: str
    inverse: str
    from_kinds: tuple[str, ...] = ()
    to_kinds: tuple[str, ...] = ()
    impact: Impact
    check_dependency: bool = False


class OfferMode(StrEnum):
    """How a capability serves a need; a task's mode maps one to one (`work` → `delegate`)."""

    DELEGATE = "delegate"
    CONSULT = "consult"
    CHECK = "check"


class TaskMode(StrEnum):
    WORK = "work"
    CONSULT = "consult"
    CHECK = "check"


class AgentDecl(Contract):
    preset: str
    model: str
    """A named model slot from instance configuration, never a model."""
    effort: str | None = None


class SkillsDecl(Contract):
    library: tuple[str, ...] = ()
    start: tuple[str, ...] = ()


class ToolboxDecl(Contract):
    image: str | None = None
    tool_servers: tuple[str, ...] = ()


class WorkspaceDecl(Contract):
    mode: Literal["write", "read_only"]
    provider: str | None = None
    """For `write`: the workspace provider that prepares and collects it."""


class PermissionsDecl(Contract):
    allow: tuple[str, ...] = ()
    """Agent-neutral permission categories, such as `read`, `write`, `shell`, `web`."""
    otherwise: Literal["deny", "decision"] = "deny"


class ProducesDecl(Contract):
    reports: tuple[str, ...] = ()
    """Paths to the report JSON Schemas the capability may submit."""
    kinds: tuple[str, ...] = ()


class OfferDecl(Contract):
    need: str
    modes: tuple[OfferMode, ...] = Field(min_length=1)
    accepts: tuple[str, ...] = ()
    yields: str | None = None
    tags: tuple[str, ...] = ()


class MayCheckDecl(Contract):
    method: str
    subjects: tuple[str, ...] = ()


class LimitsDecl(Contract):
    """Overrides of the instance's liveness timeout and consult ceiling."""

    liveness_seconds: int | None = None
    consult_ceiling_seconds: int | None = None


class CapabilityDecl(Contract):
    """A specialist, as a versioned, hashed file (Concepts, "Capability")."""

    id: str
    version: str
    prompt: str
    """Path to the prompt file within the factory."""
    agent: AgentDecl
    skills: SkillsDecl = SkillsDecl()
    toolbox: ToolboxDecl = ToolboxDecl()
    workspace: WorkspaceDecl
    permissions: PermissionsDecl = PermissionsDecl()
    produces: ProducesDecl = ProducesDecl()
    offers: tuple[OfferDecl, ...] = ()
    may_check: tuple[MayCheckDecl, ...] = ()
    tier: str
    limits: LimitsDecl = LimitsDecl()


class CheckDecl(Contract):
    method: str
    by: str
    """The prover: a need, or the check station for a mechanical method."""
    required: bool = True
    targets: tuple[str, ...] = ()


class TaskStep(Contract):
    type: Literal["task"] = "task"
    name: str
    need: str
    mode: TaskMode = TaskMode.WORK
    inputs: tuple[str, ...] = ()
    output: str | None = None
    checks: tuple[CheckDecl, ...] = ()
    limits: LimitsDecl = LimitsDecl()


class DeliverStep(Contract):
    type: Literal["deliver"] = "deliver"
    name: str
    adapter: str
    source: str = Field(alias="from")
    """The `task` step whose subject is delivered."""


TemplateStep = Annotated[TaskStep | DeliverStep, Field(discriminator="type")]
"""M1 templates are linear sequences of `task` and `deliver` steps (REQ-0308)."""


class TemplateDecl(Contract):
    name: str
    command: str
    args: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])
    """A JSON Schema for the command's arguments."""
    steps: tuple[TemplateStep, ...] = Field(min_length=1)


class CheckShape(StrEnum):
    """The six kernel execution shapes every check method maps to (REQ-0309)."""

    COMMAND = "command"
    TEST = "test"
    REPRODUCE = "reproduce"
    CROSS_TOOL = "cross_tool"
    REVIEW = "review"
    MANUAL = "manual"


class CheckMethodDecl(Contract):
    name: str
    shape: CheckShape
    env_relevant: bool = False
    config_schema: str | None = None


class FactoryManifest(Contract):
    """A factory's `manifest.yaml`: every name it registers, all in its own namespace."""

    schema_version: Literal[1] = 1
    name: str
    """The factory's namespace."""
    version: str
    sdk: str
    """A PEP 440 specifier set the running SDK must satisfy, such as `>=0.1.0,<0.2.0`."""
    kinds: tuple[KindDecl, ...] = ()
    edges: tuple[EdgeDecl, ...] = ()
    capabilities: tuple[str, ...] = ()
    """Paths to capability files within the factory."""
    templates: tuple[TemplateDecl, ...] = ()
    check_methods: tuple[CheckMethodDecl, ...] = ()
    workspace_providers: tuple[str, ...] = ()
    delivery_adapters: tuple[str, ...] = ()
    decision_kinds: tuple[str, ...] = ()
    secrets: tuple[str, ...] = ()
    config_schema: str | None = None
    """Path to a JSON Schema for this factory's project section; without one it accepts none."""
    code: str | None = None
    """A module whose `ADAPTERS` maps adapter and method names to classes."""


# Configuration: validated, hashed data that no agent can reach (I-14).

IMAGE_REFERENCE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")
"""An image pinned by digest: `name@sha256:<64 hex>`, with or without a tag."""

EXACT_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.+-]+)?$")
"""An exact version such as `0.1.0`, never a range."""

SECRET_NAME = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)?$")
"""Unprefixed for the kernel's own secrets (SPEC-05), `<namespace>.<name>` for a factory's."""


def _image_reference(value: str) -> str:
    if not IMAGE_REFERENCE.match(value):
        raise ValueError("an image is pinned by digest, as name@sha256:<64 hex digits>")
    return value


def _secret_path(value: str) -> str:
    # The rule never repeats the value: a misplaced secret must not reach a log.
    absolute = PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()
    if not absolute or any(c.isspace() for c in value):
        raise ValueError("a secret is named by the absolute path of its file, never by its value")
    return value


def _secret_name(value: str) -> str:
    if not SECRET_NAME.match(value):
        raise ValueError("a secret name is `name` for the kernel or `<namespace>.<name>`")
    return value


def _exact_version(value: str) -> str:
    if not EXACT_VERSION.match(value):
        raise ValueError("an exact version such as 0.1.0, never a range")
    return value


ImageReference = Annotated[str, AfterValidator(_image_reference)]
SecretPath = Annotated[str, AfterValidator(_secret_path)]
SecretName = Annotated[str, AfterValidator(_secret_name)]
ExactVersion = Annotated[str, AfterValidator(_exact_version)]


class PlatformSection(Contract):
    """`[platform]`, this specification's own instance section."""

    factories_allowed: tuple[str, ...] | None = None
    """The factory namespaces a project may enable; unset admits every loaded factory."""


class InstanceConfig(Contract):
    """`grindstone.toml`: one typed contract whose sections their owners contribute.

    Secrets appear only as the paths of their files (REQ-0310). Each section
    another specification owns stays an open table until that specification's
    ticket types it; the keys named below are the ones it states.
    """

    schema_version: Literal[1] = 1
    store: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])
    """SPEC-02's `StoreSettings`: `database`, `blobs_dir`, `max_blob_bytes`, `max_project_bytes`."""
    stations: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])
    """SPEC-06 part 1: `[stations.<id>]` with `kind`, `tier`, `control_url` or `runs_dir`."""
    agents: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])
    """SPEC-06 part 2: `[agents.<preset>].models` (slot to model) and `force_preset`."""
    limits: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])
    """SPEC-06 part 2: `liveness_timeout`, `corrective_prompts`, `park_backoff`."""
    host: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])
    """SPEC-06 part 1: `transcript_truncate`, `resume_window`."""
    checks: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])
    """SPEC-08: `log_truncate`, `junit_max_bytes`."""
    delivery: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])
    """SPEC-08: `observe_seconds`."""
    surface: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])
    """SPEC-07's `mcp_*` keys and SPEC-10's session, cookie and rate-limit keys."""
    platform: PlatformSection = PlatformSection()
    images: dict[str, ImageReference] = Field(default_factory=dict[str, ImageReference])
    """Image name to digest-pinned reference; projects choose among these."""
    secrets: dict[SecretName, SecretPath] = Field(default_factory=dict[SecretName, SecretPath])
    """Secret name to the path of its file; a value never appears in configuration."""


class ProjectSection(Contract):
    name: str = Field(min_length=1)


class FactoryEntry(Contract):
    """A factory a project enables: its exact version and its project section.

    In TOML, `[factories]` maps a namespace to its version (`notes = "0.1.0"`),
    or `[factories.<ns>]` holds `version` beside the keys of the factory's own
    section, which that factory's `config_schema` validates.
    """

    version: ExactVersion
    section: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])


class GrantsSection(Contract):
    tiers: tuple[str, ...] = ()
    secrets: tuple[str, ...] = ()
    """Factory secrets this project lets their own factory read (REQ-0315)."""


class ProjectChecks(Contract):
    image: str | None = None
    """A name from the instance's `[images]`."""


class CapabilityOverride(Contract):
    """The bounded fields a project may override (Concepts, "Where capabilities come from")."""

    model: str | None = None
    """A model slot name, as in `CapabilityDecl`, never a model."""
    effort: str | None = None
    limits: LimitsDecl | None = None
    extra_prompt: str | None = None


class ProjectConfig(Contract):
    """A project's configuration, held by the control plane as numbered versions (REQ-0311)."""

    schema_version: Literal[1] = 1
    project: ProjectSection
    factories: dict[str, FactoryEntry] = Field(default_factory=dict[str, FactoryEntry])
    grants: GrantsSection = GrantsSection()
    checks: ProjectChecks = ProjectChecks()
    capabilities: dict[str, CapabilityOverride] = Field(
        default_factory=dict[str, CapabilityOverride]
    )
