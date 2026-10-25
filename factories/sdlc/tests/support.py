"""Helpers for the `sdlc` factory's tests: loading it, and reading its template.

The template's inputs and check targets are strings whose grammar the
manifest's header states. The template runner (SPEC-06 part 2, TKT-0601) and
`plan_checks` (SPEC-08, TKT-0801) will interpret them; until then these
helpers read them the same way, so the tests can show that the shipped
template selects what SPEC-09 says it selects.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from pydantic import JsonValue

import grindstone_sdlc
from grindstone.contracts.platform import TaskStep
from grindstone.platform import Registries, core_registries
from grindstone.platform.loader import FactorySource, LoadedFactory, LoadReport, load_factories
from grindstone.platform.registries import SDK_VERSION

PACKAGE = Path(grindstone_sdlc.__file__).parent
"""The installed package directory holding the shipped manifest."""


def load_sdlc(
    directory: Path = PACKAGE, *, sdk_version: str = SDK_VERSION
) -> tuple[Registries, LoadReport]:
    """Load the factory from `directory` into fresh registries holding the `core` names."""
    registries = core_registries()
    source = FactorySource.from_directory("sdlc", "grindstone_sdlc", directory)
    return registries, load_factories(registries, [source], sdk_version=sdk_version)


_SELECTION = re.compile(
    r"^(?P<kind>[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+)(?:\[(?P<where>[^]]+)\])?$"
)


@dataclass(frozen=True, slots=True)
class Selection:
    """A kind, optionally with the values a field must hold."""

    kind: str
    where: Mapping[str, frozenset[str]]

    def matches(self, kind: str, fields: Mapping[str, JsonValue]) -> bool:
        return kind == self.kind and all(
            str(fields.get(name)) in values for name, values in self.where.items()
        )


def selection(text: str) -> Selection:
    """`sdlc.criterion` or `sdlc.criterion[method=manual|command]`."""
    match = _SELECTION.match(text)
    if match is None:
        raise ValueError(f"{text!r} is not a selection")
    where: dict[str, frozenset[str]] = {}
    for term in (match["where"] or "").split(","):
        if term:
            name, _, values = term.partition("=")
            where[name.strip()] = frozenset(v.strip() for v in values.split("|"))
    return Selection(match["kind"], where)


@dataclass(frozen=True, slots=True)
class StepInputs:
    """A task step's inputs: where the closure starts, the edges followed, what is refused."""

    start: str
    follow: tuple[tuple[str, bool], ...]
    """Each edge type, with True when it is followed from its target back to its source."""
    refuse: tuple[Selection, ...]


def step_inputs(step: TaskStep) -> StepInputs:
    start, *rest = step.inputs
    follow: list[tuple[str, bool]] = []
    refuse: list[Selection] = []
    for entry in rest:
        verb, _, operand = entry.partition(" ")
        if verb == "follow":
            follow.append((operand.removeprefix("~"), operand.startswith("~")))
        elif verb == "refuse":
            refuse.append(selection(operand))
        else:
            raise ValueError(f"{entry!r} is not an input")
    return StepInputs(start, tuple(follow), tuple(refuse))


def task_step(factory: LoadedFactory, template: str, name: str) -> TaskStep:
    """One task step of one of the factory's templates, by name."""
    decl = next(t for t in factory.manifest.templates if t.name == template)
    step = next(s for s in decl.steps if s.name == name)
    assert isinstance(step, TaskStep)
    return step


def refused(
    inputs: StepInputs, items: Mapping[str, tuple[str, Mapping[str, JsonValue]]]
) -> list[str]:
    """The IDs of `items` (ID to kind and semantic fields) that the step refuses, sorted."""
    return sorted(
        item
        for item, (kind, fields) in items.items()
        if any(s.matches(kind, fields) for s in inputs.refuse)
    )


class Validator:
    """A JSON Schema (draft 2020-12) validator, typed for strict checking."""

    def __init__(self, schema: Mapping[str, Any]) -> None:
        self._validator = cast(Any, Draft202012Validator(dict(schema)))

    def is_valid(self, instance: object) -> bool:
        return bool(self._validator.is_valid(instance))

    def errors(self, instance: object) -> list[str]:
        return [str(e.message) for e in self._validator.iter_errors(instance)]
