"""SPEC-01, TKT-0103: canonical form, semantic hash, blob set version and golden vectors."""

import hashlib
import json
import os
import subprocess
import sys
import unicodedata
from importlib import resources
from typing import Annotated, Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import JsonValue, ValidationError

from grindstone.contracts import BlobRef, Contract, Presentation
from grindstone.contracts.base import PRESENTATION_SCHEMA_KEY
from grindstone.contracts.hashing import (
    HashInputError,
    blob_set_version,
    canonical_bytes,
    canonical_bytes_of_value,
    semantic_content,
    semantic_hash,
)

SAFE = st.integers(min_value=-(2**53 - 1), max_value=2**53 - 1)


class DefaultsFixture(Contract):
    name: str
    count: int = 0
    tags: tuple[str, ...] = ()


class PresentationFixture(Contract):
    body: str
    title: Annotated[str, Presentation] = ""


class NestedFixture(Contract):
    label: str
    inner: DefaultsFixture


class JsonFixture(Contract):
    data: dict[str, JsonValue]


FIXTURES: dict[str, type[Contract]] = {
    "DefaultsFixture": DefaultsFixture,
    "PresentationFixture": PresentationFixture,
    "NestedFixture": NestedFixture,
}


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")


def _golden() -> dict[str, Any]:
    path = resources.files("grindstone.contracts") / "golden" / "hash-vectors.json"
    return json.loads(path.read_text(encoding="utf-8"))


@given(st.text(), SAFE, st.lists(st.text(), max_size=4))
def test_hash_format_and_definition(name: str, count: int, tags: list[str]) -> None:
    contract = DefaultsFixture(name=name, count=count, tags=tuple(tags))
    digest = semantic_hash(contract)
    assert digest.startswith("sha256:")
    assert len(digest) == 71
    assert digest[7:] == digest[7:].lower()
    assert digest == "sha256:" + hashlib.sha256(canonical_bytes(contract)).hexdigest()


@given(st.text(), st.text(), st.text(), st.text())
def test_presentation_edits_never_change_hash(
    body: str, title_a: str, title_b: str, other: str
) -> None:
    a = PresentationFixture(body=body, title=title_a)
    b = PresentationFixture(body=body, title=title_b)
    assert semantic_hash(a) == semantic_hash(b)
    if _norm(other) != _norm(body):
        assert semantic_hash(PresentationFixture(body=other, title=title_a)) != semantic_hash(a)


@given(st.text())
def test_normalisation_before_hashing(text: str) -> None:
    nfd = unicodedata.normalize("NFD", text)
    nfc = unicodedata.normalize("NFC", text)
    assert semantic_hash(DefaultsFixture(name=nfd)) == semantic_hash(DefaultsFixture(name=nfc))
    lf = text.replace("\r", "")
    assert semantic_hash(DefaultsFixture(name=lf.replace("\n", "\r\n"))) == semantic_hash(
        DefaultsFixture(name=lf)
    )
    assert semantic_hash(JsonFixture(data={nfd: nfd})) == semantic_hash(
        JsonFixture(data={nfc: nfc})
    )


def test_keys_colliding_after_nfc_refused() -> None:
    with pytest.raises(HashInputError) as caught:
        semantic_hash(JsonFixture(data={"é": 1, "é": 2}))
    assert caught.value.envelope.code == "hash_input_invalid"


def test_floats_and_unsafe_integers_refused() -> None:
    with pytest.raises(TypeError, match="float"):

        class _Floaty(Contract):  # pyright: ignore[reportUnusedClass]
            ratio: float

    with pytest.raises(TypeError, match="float"):

        class _NestedFloat(Contract):  # pyright: ignore[reportUnusedClass]
            ratios: tuple[float, ...] | None = None

    class _Presented(Contract):
        ratio: Annotated[float, Presentation] = 0.5

    assert semantic_hash(_Presented()) == semantic_hash(_Presented(ratio=2.5))

    for bad in (2**53, -(2**53)):
        with pytest.raises(ValidationError, match="outside"):
            DefaultsFixture(name="x", count=bad)
    DefaultsFixture(name="x", count=2**53 - 1)


def test_unordered_collections_refused() -> None:
    with pytest.raises(TypeError, match="set"):

        class _Set(Contract):  # pyright: ignore[reportUnusedClass]
            tags: set[str]

    with pytest.raises(TypeError, match="set"):

        class _Frozen(Contract):  # pyright: ignore[reportUnusedClass]
            tags: frozenset[str] | None = None

    with pytest.raises(TypeError, match="set"):

        class _Deep(Contract):  # pyright: ignore[reportUnusedClass]
            groups: tuple[dict[str, frozenset[int]], ...]


def test_hash_is_stable_across_processes() -> None:
    script = (
        "from grindstone.contracts.errors import ErrorEnvelope, ErrorClass\n"
        "from grindstone.contracts.hashing import semantic_hash\n"
        "keys = {f'k{i}': i for i in range(50)}\n"
        "print(semantic_hash(ErrorEnvelope(code='report_invalid',"
        " error_class=ErrorClass.VALIDATION,"
        " message='m', detail=keys, retryable=False)))\n"
    )
    digests: set[str] = set()
    for seed in ("0", "1", "4242"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        out = subprocess.run(
            [sys.executable, "-c", script], env=env, capture_output=True, text=True, check=True
        )
        digests.add(out.stdout.strip())
    assert len(digests) == 1


def test_json_fields_checked_at_hash_time() -> None:
    unhashable: list[dict[str, JsonValue]] = [{"x": 1.5}, {"x": 2**53}, {"x": [-(2**53)]}]
    for data in unhashable:
        contract = JsonFixture(data=data)
        with pytest.raises(HashInputError) as caught:
            semantic_hash(contract)
        assert caught.value.envelope.code == "hash_input_invalid"
    smuggled = JsonFixture.model_construct(data={"x": b"bytes"})
    with pytest.raises(HashInputError, match="not a JSON value"):
        semantic_hash(smuggled)


def test_added_default_field_keeps_hashes() -> None:
    class V1(Contract):
        name: str

    class V2(Contract):
        name: str
        note: str | None = None
        extras: tuple[str, ...] = ()

    assert semantic_hash(V1(name="a")) == semantic_hash(V2(name="a"))
    assert semantic_hash(V1(name="a")) != semantic_hash(V2(name="a", note="n"))


def _substitute(value: Any, pointer: str) -> Any:
    *parents, last = pointer.lstrip("/").split("/")
    target = value
    for part in parents:
        target = target[part]
    target[last] = b"non-json"
    return value


def test_python_golden_vectors() -> None:
    golden = _golden()
    assert golden["vectors"]
    assert golden["refusals"]
    for vector in golden["vectors"]:
        canonical = canonical_bytes_of_value(vector["input"])
        assert canonical.decode("utf-8") == vector["canonical"], vector["name"]
        assert "sha256:" + hashlib.sha256(canonical).hexdigest() == vector["hash"], vector["name"]
        spec = vector.get("contract")
        if spec and spec["model"] == "blob_set_version":
            members = [BlobRef.model_validate(m) for m in spec["fields"]["members"]]
            assert blob_set_version(members) == vector["hash"], vector["name"]
        elif spec:
            contract = FIXTURES[spec["model"]].model_validate(spec["fields"])
            assert semantic_content(contract) == vector["input"], vector["name"]
            assert semantic_hash(contract) == vector["hash"], vector["name"]
    for refusal in golden["refusals"]:
        value = refusal["input"]
        if "substitute" in refusal:
            value = _substitute(value, refusal["substitute"]["pointer"])
        with pytest.raises(HashInputError) as caught:
            canonical_bytes_of_value(value)
        assert caught.value.envelope.code == refusal["code"], refusal["name"]


def test_blob_set_version() -> None:
    a = BlobRef(sha256="sha256:" + "1" * 64, media_type="text/plain", size=1)
    b = BlobRef(sha256="sha256:" + "2" * 64, media_type="text/plain", size=2)
    relabelled = BlobRef(sha256=a.sha256, media_type="text/markdown", size=1)
    assert blob_set_version([a, b]) == blob_set_version([b, a])
    assert blob_set_version([a, b]) == blob_set_version([b, relabelled])
    assert blob_set_version([a, b]) != blob_set_version([a])
    golden = next(v for v in _golden()["vectors"] if v["name"] == "blob set version")
    assert blob_set_version([a, b]) == golden["hash"]


def test_presentation_mark_is_in_the_schema() -> None:
    properties = PresentationFixture.model_json_schema(mode="serialization")["properties"]
    assert properties["title"][PRESENTATION_SCHEMA_KEY] is True
    assert PRESENTATION_SCHEMA_KEY not in properties["body"]
