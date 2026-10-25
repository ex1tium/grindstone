"""Factory manifests: what a factory declares, as data (SPEC-03, ADR-21, ADR-23).

A manifest is validated before any of the factory's code runs. These models
fix its shape; the loader (TKT-0302) applies the rules that span fields and
factories: namespaces, references, make and prove, check shapes, templates.
"""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, JsonValue

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
    code: str | None = None
    """A module whose `ADAPTERS` maps adapter and method names to classes."""
