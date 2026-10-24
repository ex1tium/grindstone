"""Semantic hashing: the canonical form of a contract's semantic content (SPEC-01, ADR-44).

1. Take the semantic fields, recursing into nested contracts with each one's own set.
2. Omit any field whose value equals its declared default.
3. Serialise to JSON values: enums by value, UUIDs and dates as strings.
4. Normalise every string, keys included, to NFC and line endings to LF;
   refuse keys that collide after normalisation, and any float, unsafe
   integer or non-JSON value, with `hash_input_invalid`.
5. Canonicalise with RFC 8785.
6. Hash the UTF-8 bytes with SHA-256, written `sha256:<hex>`.

The TypeScript twin in `@grindstone/contracts` runs steps 4 to 6 on the same
projected values; the golden vectors in `golden/hash-vectors.json` bind both.
"""

import hashlib
import unicodedata
from collections.abc import Iterable
from typing import Any, cast

import rfc8785
from pydantic_core import to_jsonable_python

from grindstone.contracts.base import MAX_SAFE_INTEGER, Contract
from grindstone.contracts.errors import ErrorClass, ErrorEnvelope
from grindstone.contracts.refs import BlobRef, SemanticHash


class HashInputError(ValueError):
    """Content that cannot be hashed the same way everywhere, with code `hash_input_invalid`."""

    def __init__(self, message: str, *, pointer: str) -> None:
        super().__init__(f"{message} at {pointer or '/'}")
        self.envelope = ErrorEnvelope(
            code="hash_input_invalid",
            error_class=ErrorClass.VALIDATION,
            message=message,
            detail={"pointer": pointer},
            retryable=False,
        )


class BlobSetMembers(Contract):
    """The content of a blob set's version: its members' sorted, unique content hashes."""

    members: tuple[str, ...]


def semantic_content(contract: Contract) -> dict[str, object]:
    """Steps 1 to 3: the JSON value of a contract's semantic fields, defaults omitted."""
    out: dict[str, object] = {}
    for name in contract.semantic_fields:
        value = getattr(contract, name)
        field = type(contract).model_fields[name]
        if not field.is_required() and value == field.get_default(call_default_factory=True):
            continue
        # JSON-typed fields reach normalisation as they are, so non-JSON is refused.
        out[name] = value if name in contract.json_fields else _project(value)
    return out


def _project(value: object) -> object:
    if isinstance(value, Contract):
        return semantic_content(value)
    if isinstance(value, (tuple, list)):
        return [_project(v) for v in cast("tuple[object, ...]", value)]
    if isinstance(value, dict):
        return {k: _project(v) for k, v in cast("dict[str, object]", value).items()}
    return to_jsonable_python(value)


def normalise(value: object, pointer: str = "") -> object:
    """Step 4: NFC and LF for every string and key; refuse what cannot hash alike everywhere."""
    if isinstance(value, str):
        return _text(value)
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
            raise HashInputError(f"integer {value} is outside ±(2^53 - 1)", pointer=pointer)
        return value
    if isinstance(value, float):
        raise HashInputError("a float cannot be hashed", pointer=pointer)
    if isinstance(value, list):
        return [normalise(v, f"{pointer}/{i}") for i, v in enumerate(cast("list[object]", value))]
    if isinstance(value, dict):
        out: dict[str, object] = {}
        for key, item in cast("dict[object, object]", value).items():
            if not isinstance(key, str):
                raise HashInputError(f"object key {key!r} is not a string", pointer=pointer)
            norm = _text(key)
            if norm in out:
                raise HashInputError(f"keys collide after normalisation: {norm!r}", pointer=pointer)
            out[norm] = normalise(item, f"{pointer}/{_escape(norm)}")
        return out
    raise HashInputError(f"{type(value).__name__} is not a JSON value", pointer=pointer)


def canonical_bytes_of_value(value: object) -> bytes:
    """Steps 4 and 5 on an already projected JSON value."""
    return rfc8785.dumps(cast(Any, normalise(value)))


def canonical_bytes(contract: Contract) -> bytes:
    """The RFC 8785 canonical bytes of a contract's semantic content."""
    return canonical_bytes_of_value(semantic_content(contract))


def hash_bytes(data: bytes) -> SemanticHash:
    """Step 6: `sha256:` and the lowercase hex digest."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def semantic_hash(contract: Contract) -> SemanticHash:
    """The semantic hash of a contract: what freshness compares (ADR-11)."""
    return hash_bytes(canonical_bytes(contract))


def blob_set_version(members: Iterable[BlobRef]) -> SemanticHash:
    """A blob set's version: the semantic hash of its members' sorted, unique content hashes.

    Media types do not take part, so relabelling a member changes no version.
    """
    return semantic_hash(BlobSetMembers(members=tuple(sorted({m.sha256 for m in members}))))


def _text(value: str) -> str:
    return unicodedata.normalize("NFC", value).replace("\r\n", "\n").replace("\r", "\n")


def _escape(key: str) -> str:
    return key.replace("~", "~0").replace("/", "~1")
