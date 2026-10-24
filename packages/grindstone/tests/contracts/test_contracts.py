"""SPEC-01, TKT-0101: the contract base, typed IDs, references, provenance and run manifest."""

import time
import typing
import uuid

import pytest
from pydantic import TypeAdapter, ValidationError

from grindstone.contracts import (
    EXPORTED,
    AuthorKind,
    BlobRef,
    BlobSetSubject,
    GitCommitSubject,
    ItemId,
    ItemRef,
    Provenance,
    RunId,
    RunManifest,
    TaskId,
    item_id_type,
    new_record_id,
)
from grindstone.contracts.hashing import semantic_hash

H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64


def _manifest(items: list[ItemRef]) -> RunManifest:
    return RunManifest(
        run=RunId(uuid.UUID("01a16ea7-72ff-7188-95d0-b9440badb93f")),
        task=TaskId(uuid.UUID("01a16ea7-7300-7000-8000-000000000001")),
        items=tuple(items),
        capability="sdlc.implementer",
        capability_hash=H1,
        factory="sdlc",
        factory_version="0.1.0",
        provider="anthropic",
        model="primary",
        subject=GitCommitSubject(repo="ex1tium/grindstone-testbed", sha="a" * 40),
        context_pack_hash=H1,
        instance_config_hash=H2,
        project_config_hash=H1,
        prompts=(BlobRef(sha256=H2, media_type="text/markdown", size=10),),
    )


def test_contract_is_frozen_and_closed() -> None:
    ref = ItemRef(id="REQ-0101", hash=H1)
    with pytest.raises(ValidationError):
        ref.id = "REQ-0102"
    with pytest.raises(ValidationError):
        ItemRef.model_validate({"id": "REQ-0101", "hash": H1, "extra": 1})


def test_exported_models_have_schema_version() -> None:
    for model in EXPORTED:
        field = model.model_fields.get("schema_version")
        assert field is not None, f"{model.__name__} has no schema_version"
        assert typing.get_origin(field.annotation) is typing.Literal, model.__name__
        (version,) = typing.get_args(field.annotation)
        assert type(version) is int, model.__name__


def test_typed_item_ids() -> None:
    base: TypeAdapter[str] = TypeAdapter(ItemId)
    for good in ("ABC", "X1", "X1-01", "N-3", "X-12-3"):
        assert base.validate_python(good) == good
    for bad in ("x-1", "N-", "-3", "N-1-2-3"):
        with pytest.raises(ValidationError):
            base.validate_python(bad)

    notes: TypeAdapter[str] = TypeAdapter(item_id_type("notes.note", r"^N-[0-9]+$", ("N-3",)))
    assert notes.validate_python("N-3") == "N-3"
    with pytest.raises(ValidationError):
        notes.validate_python("P-3")

    loose: TypeAdapter[str] = TypeAdapter(item_id_type("loose", r"^.*$", ("ABC",)))
    with pytest.raises(ValidationError):
        loose.validate_python("x-1")

    with pytest.raises(ValueError, match="does not match"):
        item_id_type("notes.note", r"^N-[0-9]+$", ("P-3",))
    with pytest.raises(ValidationError):
        item_id_type("loose", r"^.*$", ("x-1",))
    with pytest.raises(ValueError, match="anchored"):
        item_id_type("notes.note", r"N-[0-9]+", ("N-3",))


def test_run_manifest_fields_and_round_trip() -> None:
    m1_06 = {
        "items",
        "capability_hash",
        "factory_version",
        "provider",
        "model",
        "subject",
        "context_pack_hash",
        "prompts",
        "instance_config_hash",
        "project_config_hash",
    }
    assert m1_06 <= set(RunManifest.model_fields)
    manifest = _manifest([ItemRef(id="AC-0101-1", hash=H1)])
    assert RunManifest.model_validate_json(manifest.model_dump_json()) == manifest


def test_run_manifest_hash_is_order_independent() -> None:
    a = ItemRef(id="REQ-0101", hash=H1)
    b = ItemRef(id="AC-0101-1", hash=H2)
    first, second = _manifest([a, b]), _manifest([b, a])
    assert first == second
    assert first.model_dump_json() == second.model_dump_json()
    assert semantic_hash(first) == semantic_hash(second)
    assert [i.id for i in first.items] == ["AC-0101-1", "REQ-0101"]
    assert _manifest([a, a, b]) == first
    with pytest.raises(ValidationError, match="one revision of each item"):
        _manifest([a, ItemRef(id="REQ-0101", hash=H2)])


def test_record_ids_are_uuid7() -> None:
    ids: list[uuid.UUID] = []
    for _ in range(3):
        ids.append(new_record_id())
        time.sleep(0.002)
    assert all(i.version == 7 for i in ids)
    assert ids == sorted(ids)
    assert (
        Provenance(
            author_kind=AuthorKind.SYSTEM, author="kernel", task=TaskId(ids[0]), reason="seed"
        ).task
        == ids[0]
    )


def test_reference_hash_forms() -> None:
    BlobRef(sha256=H1, media_type="application/octet-stream", size=0)
    for bad in ("1" * 64, "sha256:" + "A" * 64, "sha256:" + "1" * 63, "sha1:" + "1" * 40):
        with pytest.raises(ValidationError):
            BlobRef(sha256=bad, media_type="text/plain", size=1)
    with pytest.raises(ValidationError):
        BlobRef(sha256=H1, media_type="text/plain", size=-1)

    for good in ("a" * 40, "b" * 64):
        GitCommitSubject(repo="r", sha=good)
    for bad in ("a" * 39, "A" * 40, "a" * 41):
        with pytest.raises(ValidationError):
            GitCommitSubject(repo="r", sha=bad)

    members = (
        BlobRef(sha256=H2, media_type="a/b", size=1),
        BlobRef(sha256=H1, media_type="a/b", size=1),
    )
    assert [m.sha256 for m in BlobSetSubject(members=members).members] == [H1, H2]
    with pytest.raises(ValidationError, match="distinct content hashes"):
        BlobSetSubject(members=(members[0], BlobRef(sha256=H2, media_type="c/d", size=1)))
