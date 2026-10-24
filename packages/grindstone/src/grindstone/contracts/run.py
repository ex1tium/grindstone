"""The run manifest: everything one task run was given (I-06, M1-06).

`stations` records it before a session opens (SPEC-06); its semantic hash
identifies exactly what the run used, so its items are held sorted by ID.
"""

from typing import Any, Literal, cast

from pydantic import model_validator

from grindstone.contracts.base import Contract
from grindstone.contracts.ids import RunId, TaskId
from grindstone.contracts.refs import BlobRef, ItemRef, SemanticHash, SubjectRef


class RunManifest(Contract):
    """The pinned inputs, configuration and prompts of one task run."""

    schema_version: Literal[1] = 1
    run: RunId
    task: TaskId
    items: tuple[ItemRef, ...]
    capability: str
    capability_hash: SemanticHash
    factory: str
    factory_version: str
    provider: str
    model: str
    subject: SubjectRef | None
    context_pack_hash: SemanticHash
    instance_config_hash: SemanticHash
    project_config_hash: SemanticHash
    prompts: tuple[BlobRef, ...]

    @model_validator(mode="before")
    @classmethod
    def _sort_items(cls, data: object) -> object:
        """Sort pinned items by ID, so equal manifests hash equally; one revision per item."""
        if not isinstance(data, dict):
            return data
        raw = cast(dict[str, Any], data)
        if "items" in raw:
            pinned = {(r.id, r.hash): r for r in map(ItemRef.model_validate, raw["items"])}
            unique = sorted(pinned.values(), key=lambda r: r.id)
            ids = [r.id for r in unique]
            if len(set(ids)) != len(ids):
                raise ValueError("a run pins one revision of each item")
            return {**raw, "items": tuple(unique)}
        return raw
