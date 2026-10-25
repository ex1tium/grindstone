"""SPEC-03, TKT-0301: registries, the `core` names, provenance and the SDK 0.1.0 surface."""

import inspect
import typing
from pathlib import Path

import pytest
from tests.fitness.helpers import copy_sources, lint_imports

from grindstone import sdk
from grindstone.contracts import EXPORTED, ErrorClass, bundle_schema, error_class_of, ports
from grindstone.platform import (
    CORE,
    Category,
    Origin,
    Registries,
    RegistryError,
    core_registries,
    loading,
    register_error_code,
)

NOTES = Origin("notes", "0.1.0", "sha256:" + "a" * 64)

SDK_EXPORTS = {
    "SPEC-01": {
        "ItemRef",
        "BlobRef",
        "SubjectRef",
        "SemanticHash",
        "ErrorEnvelope",
        "item_id_type",
        "semantic_hash",
    },
    "SPEC-03": {
        "FactoryManifest",
        "KindDecl",
        "FieldDecl",
        "EdgeDecl",
        "CapabilityDecl",
        "TemplateDecl",
        "CheckMethodDecl",
        "Context",
        "ItemReader",
        "BlobReader",
        "FactoryStorage",
        "SecretReader",
        "register_error_code",
    },
}
"""SPEC-03's export table, by owner; SPEC-06 part 1 and SPEC-08 add their rows with their ports."""

PORT_PROTOCOLS = (
    "Context",
    "WorkspaceProvider",
    "SubjectResolver",
    "CheckMethod",
    "DeliveryAdapter",
)


def test_core_names_registered_first() -> None:
    registries = core_registries()
    assert registries.names(Category.KIND) == (
        "core.finding",
        "core.interface",
        "core.learning",
        "core.observation",
        "core.principle",
    )
    assert set(registries.names(Category.NEED)) == {"core.review.impact", "core.advise", "operator"}
    assert set(registries.names(Category.CHECK_SHAPE)) == {
        "command",
        "test",
        "reproduce",
        "cross_tool",
        "review",
        "manual",
    }
    assert set(registries.names(Category.SUBJECT_KIND)) == {
        "git_commit",
        "blob",
        "blob_set",
        "item_revision",
    }
    assert set(registries.names(Category.DECISION_KIND)) == {
        "approval",
        "question",
        "permission",
        "delivery",
        "escalation",
    }
    assert registries.require(Category.ERROR_CODE, "name_conflict").value is ErrorClass.VALIDATION
    assert all(e.origin.factory == CORE for e in registries.entries())

    with pytest.raises(RegistryError) as caught:
        registries.register(Category.KIND, "core.note", None, NOTES)
    assert caught.value.envelope.code == "manifest_invalid"


def test_factory_names_stay_in_their_namespace() -> None:
    registries = core_registries()
    registries.register(Category.NEED, "notes.write", None, NOTES)
    for name in ("other.write", "write", "notesx.write"):
        with pytest.raises(RegistryError) as caught:
            registries.register(Category.NEED, name, None, NOTES)
        assert caught.value.envelope.code == "manifest_invalid"
    with pytest.raises(RegistryError) as caught:
        registries.register(Category.NEED, "notes.write", None, NOTES)
    assert caught.value.envelope.code == "name_conflict"
    registries.freeze()
    with pytest.raises(RegistryError, match="frozen"):
        registries.register(Category.NEED, "notes.review", None, NOTES)


def test_registry_provenance_lookups() -> None:
    # The loader (TKT-0302) records the same values in `platform.factories`;
    # this checks the registry side of AC-0317-1.
    registries = Registries()
    capability_hash = "sha256:" + "c" * 64
    registries.register(
        Category.CAPABILITY, "notes.writer", None, NOTES, capability_hash=capability_hash
    )
    entry = registries.require(Category.CAPABILITY, "notes.writer")
    assert entry.origin.factory == "notes"
    assert entry.origin.version == "0.1.0"
    assert entry.origin.manifest_hash == NOTES.manifest_hash
    assert entry.capability_hash == capability_hash
    with pytest.raises(KeyError, match=r"notes.reader"):
        registries.require(Category.CAPABILITY, "notes.reader")


def test_factory_error_codes_register_only_while_loading() -> None:
    registries = core_registries()
    with pytest.raises(RegistryError, match="only while the kernel loads"):
        register_error_code("notes.too_long", ErrorClass.VALIDATION)
    with loading(registries, NOTES):
        register_error_code("notes.too_long", ErrorClass.VALIDATION)
    assert registries.require(Category.ERROR_CODE, "notes.too_long").origin == NOTES
    assert error_class_of("notes.too_long") is ErrorClass.VALIDATION


def test_sdk_exports_the_table() -> None:
    expected: set[str] = set[str]().union(*SDK_EXPORTS.values())
    assert set(sdk.__all__) == expected
    assert sdk.__version__ == "0.1.0"
    assert all(hasattr(sdk, name) for name in expected)


def _probe(root: Path, package_dir: str, statement: str) -> str:
    (root / package_dir / "_ff_probe.py").write_text(f"{statement}\n", encoding="utf-8")
    result = lint_imports(root)
    return result.stdout if result.returncode != 0 else ""


def test_ff01_factories_use_sdk_only(tmp_path: Path) -> None:
    root = copy_sources(tmp_path)
    assert _probe(root, "grindstone_notes", "import grindstone.sdk") == ""
    failure = _probe(root, "grindstone_notes", "import grindstone.platform")
    assert "Factories import only grindstone.sdk BROKEN" in failure


def test_port_protocols_live_in_contracts(tmp_path: Path) -> None:
    for name in PORT_PROTOCOLS:
        if hasattr(ports, name):
            assert getattr(sdk, name) is getattr(ports, name), name
            assert typing.is_protocol(getattr(ports, name)), name
    protocols = {n for n, v in inspect.getmembers(ports) if typing.is_protocol(v)}
    assert {"Context", "ItemReader", "BlobReader", "FactoryStorage", "SecretReader"} <= protocols
    assert not protocols & set(bundle_schema(EXPORTED, title="t")["$defs"])

    root = copy_sources(tmp_path)
    for module in ("platform", "stations", "evidence", "delivery"):
        assert _probe(root, f"grindstone/{module}", "import grindstone.contracts.ports") == ""
    failure = _probe(root, "grindstone/stations", "import grindstone.sdk")
    assert "grindstone.stations imports only" in failure
