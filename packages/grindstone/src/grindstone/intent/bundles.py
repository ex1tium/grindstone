"""Item bundles: hand-written items in YAML, imported as one ChangeDraft (SPEC-04, DEC-0401).

`parse_bundle` reads a bundle with YAML's safe loader, so a tag that would
construct an object is refused, and validates it against `ItemBundle`. Every
problem is reported together, each with the item it belongs to. Whether the
items fit their kinds, the project and each other is the ChangeSet's rule
check (`grindstone.change`).
"""

from typing import Any, cast

import yaml
from pydantic import JsonValue, ValidationError
from pydantic_core import ErrorDetails

from grindstone.contracts.intent import ItemBundle
from grindstone.intent.errors import IntentError


def parse_bundle(data: bytes) -> ItemBundle:
    """The bundle in `data`, or `IntentError("report_invalid")` listing every problem."""
    try:
        raw: Any = yaml.safe_load(data)
    except yaml.YAMLError as exc:
        raise IntentError(
            "report_invalid",
            "the bundle is not valid YAML, or uses a tag the safe loader refuses",
            problems=[{"item": None, "message": _first_line(exc)}],
        ) from None
    try:
        return ItemBundle.model_validate(raw)
    except ValidationError as exc:
        problems: list[JsonValue] = [
            {"item": _item_of(raw, error["loc"]), "message": _where(error) + error["msg"]}
            for error in exc.errors()
        ]
        raise IntentError(
            "report_invalid",
            f"the bundle does not match item bundle schema 1 ({len(problems)} problems)",
            problems=problems,
        ) from None


def _first_line(exc: yaml.YAMLError) -> str:
    return str(exc).splitlines()[0] if str(exc) else type(exc).__name__


def _where(error: ErrorDetails) -> str:
    loc = ".".join(str(part) for part in error["loc"])
    return f"{loc}: " if loc else ""


def _item_of(raw: object, loc: tuple[int | str, ...]) -> str | None:
    """The ID of the item a schema error is in, or its position when it has none."""
    if len(loc) < 2 or loc[0] != "items" or not isinstance(loc[1], int):
        return None
    index = loc[1]
    items = cast(dict[str, object], raw).get("items") if isinstance(raw, dict) else None
    entry = cast(list[object], items)[index] if isinstance(items, list) else None
    found = cast(dict[str, object], entry).get("id") if isinstance(entry, dict) else None
    return found if isinstance(found, str) else f"items[{index}]"
