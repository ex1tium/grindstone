"""The base every contract model derives from, and how schemas are generated.

One configuration for every contract keeps the generated JSON Schema and
TypeScript uniform: models are immutable, reject unknown fields, and in
serialization schemas every field with a default is required, because
Grindstone always emits it.
"""

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.json_schema import models_json_schema


class Contract(BaseModel):
    """Base class for every model in `grindstone.contracts`."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_serialization_defaults_required=True,
    )


def bundle_schema(models: Sequence[type[BaseModel]], *, title: str) -> dict[str, Any]:
    """One JSON Schema holding every model under `$defs`, in serialization mode.

    Field-level titles are dropped: they only restate the field name, and code
    generators turn them into throwaway type aliases that collide across models.
    """
    _, bundle = models_json_schema([(m, "serialization") for m in models], title=title)
    for definition in bundle.get("$defs", {}).values():
        for prop in definition.get("properties", {}).values():
            prop.pop("title", None)
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **bundle}
