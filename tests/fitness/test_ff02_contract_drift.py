"""FF-02: the committed JSON Schema bundle matches the Pydantic contracts.

The TypeScript side is regenerated from that bundle and diffed in CI
(`make gen` then `git diff --exit-code`).
"""

import json

from grindstone.contracts import EXPORTED, bundle_schema
from tests.fitness.helpers import REPO

BUNDLE = REPO / "packages" / "contracts-ts" / "schemas" / "contracts.schema.json"


def test_schema_bundle_matches_contracts() -> None:
    expected = bundle_schema(EXPORTED, title="GrindstoneContracts")
    assert json.loads(BUNDLE.read_text(encoding="utf-8")) == expected, "run `make gen`"


def test_every_exported_contract_is_in_the_bundle() -> None:
    defs = json.loads(BUNDLE.read_text(encoding="utf-8"))["$defs"]
    assert {m.__name__ for m in EXPORTED} <= set(defs)


def test_field_titles_are_dropped_and_defaults_are_required() -> None:
    defs = bundle_schema(EXPORTED, title="T")["$defs"]
    for definition in defs.values():
        for prop in definition.get("properties", {}).values():
            assert "title" not in prop
        if "properties" in definition:
            assert set(definition["required"]) == set(definition["properties"])
