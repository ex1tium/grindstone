"""Events: the envelope every state change becomes, and the kernel's event union (SPEC-03).

A module records an event in the same unit of work as the change it
describes, with a UUIDv7 event ID and a per-project sequence number with no
gaps (REQ-0313). Each event model has a literal `type` and a schema version;
the union of every kernel event model is assembled here and generated for
TypeScript like every other contract (FF-02). Factories register no event
types in SDK 0.1.0. Later specifications add their events to `KernelEvent`.
"""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, JsonValue

from grindstone.contracts.base import Contract
from grindstone.contracts.change import (
    ChangeSetApplied,
    ChangeSetDrafted,
    ChangeSetRejected,
    ChangeSetWalked,
)
from grindstone.contracts.decisions import DecisionAnswered, DecisionRaised, DecisionSuperseded
from grindstone.contracts.intent import ItemRevised, ItemTransitioned
from grindstone.contracts.refs import SemanticHash

INSTANCE_STREAM = uuid.UUID(int=0)
"""The project ID of the instance's own stream, for events no project owns."""


class EventEnvelope(Contract):
    """One recorded event: its stream, its place in it, and the event model's fields.

    `type` and `event_version` are the event model's `type` and
    `schema_version`; `payload` holds its other fields, so the envelope
    round-trips to the model.
    """

    schema_version: Literal[1] = 1
    event_id: uuid.UUID
    project: uuid.UUID
    """A project ID, or `INSTANCE_STREAM`."""
    seq: int = Field(ge=1)
    type: str
    event_version: int = Field(ge=1)
    occurred_at: datetime
    payload: dict[str, JsonValue]


class FactoryLoaded(Contract):
    """A factory passed its load at start-up."""

    schema_version: Literal[1] = 1
    type: Literal["factory.loaded"] = "factory.loaded"
    factory: str
    version: str
    manifest_hash: SemanticHash


class FactoryRefused(Contract):
    """A factory was refused at start-up, with the `file:field: rule` lines that failed."""

    schema_version: Literal[1] = 1
    type: Literal["factory.refused"] = "factory.refused"
    factory: str
    problems: tuple[str, ...]


class ProjectConfigured(Contract):
    """A project's configuration gained a version."""

    schema_version: Literal[1] = 1
    type: Literal["project.configured"] = "project.configured"
    version: int = Field(ge=1)
    hash: SemanticHash


class ConfigInvalid(Contract):
    """A project's current configuration is invalid, so the project is paused."""

    schema_version: Literal[1] = 1
    type: Literal["config.invalid"] = "config.invalid"
    problems: tuple[str, ...]


KernelEvent = Annotated[
    FactoryLoaded
    | FactoryRefused
    | ProjectConfigured
    | ConfigInvalid
    | DecisionRaised
    | DecisionAnswered
    | DecisionSuperseded
    | ItemRevised
    | ItemTransitioned
    | ChangeSetDrafted
    | ChangeSetWalked
    | ChangeSetApplied
    | ChangeSetRejected,
    Field(discriminator="type"),
]
"""Every kernel event model, discriminated on `type`."""

KERNEL_EVENT_MODELS: tuple[type[Contract], ...] = (
    FactoryLoaded,
    FactoryRefused,
    ProjectConfigured,
    ConfigInvalid,
    DecisionRaised,
    DecisionAnswered,
    DecisionSuperseded,
    ItemRevised,
    ItemTransitioned,
    ChangeSetDrafted,
    ChangeSetWalked,
    ChangeSetApplied,
    ChangeSetRejected,
)
