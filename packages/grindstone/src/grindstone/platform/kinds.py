"""Kinds declared as data, compiled into contracts (SPEC-03, REQ-0305, DEC-0301).

The field vocabulary maps onto SPEC-01's admitted types: no floats, lists as
ordered tuples, presentation fields marked `Presentation`, references as item
IDs typed by their target kinds' patterns. Every kind gets a presentation
field `title`. The compiled class derives from `Contract`, so its semantic
hash follows SPEC-01. What the fields mean at revision time is SPEC-04's.
"""

from collections.abc import Mapping
from typing import Annotated, Any, Literal, Optional, cast

from pydantic import create_model

from grindstone.contracts.base import Contract, Presentation
from grindstone.contracts.ids import ItemId, item_id_type
from grindstone.contracts.platform import Cardinality, FieldDecl, FieldType, KindDecl
from grindstone.contracts.refs import BlobRef

LIFECYCLE_WRITERS = frozenset({"changeset", "task", "evidence", "delivery"})
"""The closed set of lifecycle writers SPEC-04 defines."""


def field_problems(name: str, decl: FieldDecl) -> list[str]:
    """What is wrong with one field declaration beyond its schema, as rules."""
    problems: list[str] = []
    if decl.type is FieldType.ENUM and not decl.values:
        problems.append(f"{name}: an enum field needs values")
    if decl.type is FieldType.REF and decl.edge is None:
        problems.append(f"{name}: a ref field names its edge")
    if decl.type is FieldType.LIST:
        if decl.of is None:
            problems.append(f"{name}: a list field names its element type in `of`")
        elif decl.of.type is FieldType.LIST:
            problems.append(f"{name}: a list holds one of the other types, not a list")
        else:
            problems.extend(field_problems(f"{name}.of", decl.of))
    return problems


def kind_problems(kind: KindDecl) -> list[str]:
    """Phase-1 rules for one kind: ID pattern and examples, fields, lifecycle."""
    problems: list[str] = []
    try:
        item_id_type(kind.name, kind.id.pattern, kind.id.examples)
    except ValueError as exc:
        problems.append(f"id: {_first_line(exc)}")
    if "title" in kind.fields:
        problems.append("fields.title: every kind has a presentation `title`; it is not declared")
    for name, decl in kind.fields.items():
        problems.extend(f"fields.{p}" for p in field_problems(name, decl))
    if kind.lifecycle is not None:
        states = set(kind.lifecycle.states)
        if kind.lifecycle.initial not in states:
            problems.append(f"lifecycle.initial: {kind.lifecycle.initial!r} is not a state")
        for i, t in enumerate(kind.lifecycle.transitions):
            problems.extend(
                f"lifecycle.transitions[{i}]: {end!r} is not a state"
                for end in (t.source, t.to)
                if end not in states
            )
            if t.writer not in LIFECYCLE_WRITERS:
                problems.append(
                    f"lifecycle.transitions[{i}].writer: {t.writer!r} is not one of "
                    f"{', '.join(sorted(LIFECYCLE_WRITERS))}"
                )
    return problems


def compile_kind(kind: KindDecl, patterns: Mapping[str, str]) -> type[Contract]:
    """The contract class for a kind; `patterns` maps every known kind to its ID pattern."""
    fields: dict[str, Any] = {"title": (Annotated[str, Presentation], "")}
    for name, decl in kind.fields.items():
        annotation = _annotation(kind.name, name, decl, patterns)
        default: object = ...
        if not decl.required:
            default = _default(decl)
            if default is None:
                annotation = Optional[annotation]  # noqa: UP045 - built at run time
        # The mark must be outermost: pydantic reads field metadata only there.
        if decl.presentation:
            annotation = Annotated[annotation, Presentation]
        fields[name] = (annotation, default)
    return create_model(kind.name, __base__=Contract, **fields)


_SCALARS: Mapping[FieldType, type] = {
    FieldType.STRING: str,
    FieldType.TEXT: str,
    FieldType.INTEGER: int,
    FieldType.BOOLEAN: bool,
    FieldType.BLOB: BlobRef,
}


def _annotation(kind: str, name: str, decl: FieldDecl, patterns: Mapping[str, str]) -> object:
    scalar = _SCALARS.get(decl.type)
    if scalar is not None:
        return scalar
    if decl.type is FieldType.ENUM:
        return Literal[*decl.values]
    if decl.type is FieldType.REF:
        target = _ref_type(f"{kind}.{name}", decl.kinds, patterns)
        return tuple[target, ...] if decl.cardinality is Cardinality.MANY else target
    if decl.of is None:
        raise ValueError(f"{kind}.{name}: a list field names its element type")
    element = _annotation(kind, name, decl.of, patterns)
    return tuple[element, ...]


def _ref_type(where: str, kinds: tuple[str, ...], patterns: Mapping[str, str]) -> object:
    """An ID type admitting the target kinds' IDs; any item ID when no kind is named."""
    if not kinds:
        return ItemId
    bodies = [patterns[k].removeprefix("^").removesuffix("$") for k in sorted(kinds)]
    return item_id_type(where, "^(?:" + "|".join(bodies) + ")$", ())


def _default(decl: FieldDecl) -> object:
    value = decl.default
    if isinstance(value, list):
        return tuple(cast(list[object], value))
    return value


def _first_line(exc: Exception) -> str:
    return str(exc).splitlines()[0]
