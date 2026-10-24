"""The base every contract model derives from, and how schemas are generated.

One configuration for every contract keeps the generated JSON Schema and
TypeScript uniform: models are immutable, reject unknown fields, and in
serialization schemas every field with a default is required, because
Grindstone always emits it.

Every field is semantic unless marked `Annotated[T, Presentation]`: semantic
fields are what a semantic hash covers (SPEC-01, DEC-0101). So that the same
content hashes the same in every process and language, a contract whose
semantic fields can hold a float or an unordered collection is refused when
its class is defined, and a semantic integer outside ±(2^53 - 1) is refused
when an instance is validated. Values inside JSON-typed fields (`JsonValue`)
are checked when they are hashed instead.
"""

from collections.abc import Sequence
from typing import (
    Annotated,
    Any,
    ClassVar,
    Self,
    TypeAliasType,
    cast,
    get_args,
    get_origin,
    override,
)

from pydantic import BaseModel, ConfigDict, GetJsonSchemaHandler, JsonValue, model_validator
from pydantic.json_schema import JsonSchemaValue, models_json_schema
from pydantic_core import CoreSchema

MAX_SAFE_INTEGER = 2**53 - 1
"""The largest integer JavaScript represents exactly (DEC-0102)."""


PRESENTATION_SCHEMA_KEY = "x-grindstone-presentation"
"""Set to true on a presentation field in generated schemas, so FF-03 can see the mark."""


class _PresentationMark:
    """Marks a field as presentation: excluded from the semantic hash."""

    @override
    def __repr__(self) -> str:
        return "Presentation"

    def __get_pydantic_json_schema__(
        self, core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {**handler(core_schema), PRESENTATION_SCHEMA_KEY: True}


Presentation = _PresentationMark()
"""Use as `Annotated[T, Presentation]` for a field whose edits never change the hash."""


class Contract(BaseModel):
    """Base class for every model in `grindstone.contracts`."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_serialization_defaults_required=True,
    )

    semantic_fields: ClassVar[tuple[str, ...]] = ()
    """The fields a semantic hash covers, in declaration order."""

    json_fields: ClassVar[frozenset[str]] = frozenset()
    """Semantic fields whose type contains `JsonValue`; checked when hashed."""

    @classmethod
    @override
    def __pydantic_init_subclass__(cls, **kwargs: object) -> None:
        super().__pydantic_init_subclass__(**kwargs)
        semantic: list[str] = []
        json_typed: set[str] = set()
        for name, field in cls.model_fields.items():
            if any(m is Presentation for m in field.metadata):
                continue
            semantic.append(name)
            if _refuse_unstable(field.annotation, f"{cls.__name__}.{name}"):
                json_typed.add(name)
        cls.semantic_fields = tuple(semantic)
        cls.json_fields = frozenset(json_typed)

    @model_validator(mode="after")
    def _semantic_integers_are_safe(self) -> Self:
        for name in self.semantic_fields:
            if name not in self.json_fields:
                _check_integers(getattr(self, name), f"{type(self).__name__}.{name}")
        return self


def _refuse_unstable(annotation: object, where: str) -> bool:
    """Raise if the type can hold a float or a set; return whether it holds `JsonValue`."""
    if annotation is JsonValue:
        return True
    if annotation is float:
        raise TypeError(f"{where}: a semantic field cannot hold a float (DEC-0102)")
    origin = get_origin(annotation)
    if annotation is set or annotation is frozenset or origin in (set, frozenset):
        raise TypeError(
            f"{where}: a semantic field cannot hold a set; use a sorted tuple (REQ-0106)"
        )
    if isinstance(annotation, type) and issubclass(annotation, Contract):
        return False  # checked when its own class was defined
    if isinstance(annotation, TypeAliasType):
        return _refuse_unstable(annotation.__value__, where)
    args = get_args(annotation)
    if origin is Annotated:
        args = args[:1]
    holds_json = False
    for arg in args:
        holds_json = _refuse_unstable(arg, where) or holds_json
    return holds_json


def _check_integers(value: object, where: str) -> None:
    if isinstance(value, (bool, Contract)):
        return
    if isinstance(value, int):
        if not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
            raise ValueError(f"{where}: integer {value} is outside ±(2^53 - 1) (DEC-0102)")
    elif isinstance(value, (tuple, list)):
        for item in cast("tuple[object, ...]", value):
            _check_integers(item, where)
    elif isinstance(value, dict):
        for item in cast("dict[object, object]", value).values():
            _check_integers(item, where)


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
