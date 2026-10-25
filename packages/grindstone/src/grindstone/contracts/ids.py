"""Typed identifiers: item IDs people read and record IDs the kernel generates.

Item IDs (`REQ-0101`, `M1-01`, `N-3`, `PRD`) follow one base grammar; each
kind narrows it with its own pattern when it registers (SPEC-03). Record IDs
(runs, tasks, ChangeSets, decisions, projects) are UUIDv7, so they sort by creation time.
"""

import re
import uuid
from typing import Annotated, NewType, cast

from pydantic import AfterValidator, StringConstraints, TypeAdapter

ITEM_ID_GRAMMAR = r"^[A-Z][A-Z0-9]{0,7}(-[0-9]+){0,2}$"
"""Base grammar every item ID matches: a capitalised prefix, then up to two numbers."""

ItemId = Annotated[str, StringConstraints(pattern=ITEM_ID_GRAMMAR)]
"""An item ID of any kind. Fields that hold one kind's IDs use `item_id_type`."""

_ITEM_ID = TypeAdapter(ItemId)


def item_id_type(name: str, pattern: str, examples: tuple[str, ...]) -> type[str]:
    """A distinct ID type for one kind: the base grammar first, then the kind's pattern.

    `pattern` must be anchored (`^…$`), and every example must match both the
    pattern and the base grammar, so a kind cannot declare IDs nobody can write.
    A loose pattern never widens the base grammar, which is checked first.
    The result is an `Annotated` type for fields and `TypeAdapter`; kinds are
    registered as data, so it is built at run time and typed as the `str`
    it validates.
    """
    if not (pattern.startswith("^") and pattern.endswith("$")):
        raise ValueError(f"{name}: ID pattern {pattern!r} must be anchored with ^ and $")
    compiled = re.compile(pattern)
    for example in examples:
        _ITEM_ID.validate_python(example)
        if not compiled.fullmatch(example):
            raise ValueError(f"{name}: example ID {example!r} does not match {pattern!r}")

    def check(value: str) -> str:
        if not compiled.fullmatch(value):
            raise ValueError(f"not a {name} ID: {value!r} does not match {pattern!r}")
        return value

    return cast(
        type[str], Annotated[str, StringConstraints(pattern=ITEM_ID_GRAMMAR), AfterValidator(check)]
    )


RunId = NewType("RunId", uuid.UUID)
TaskId = NewType("TaskId", uuid.UUID)
ChangeSetId = NewType("ChangeSetId", uuid.UUID)
DecisionId = NewType("DecisionId", uuid.UUID)
ProjectId = NewType("ProjectId", uuid.UUID)


def new_record_id() -> uuid.UUID:
    """A new UUIDv7; wrap it in the record kind's type, e.g. `RunId(new_record_id())`."""
    return uuid.uuid7()
