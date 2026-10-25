# Upgrades

Upgrade steps for breaking changes to contracts (ADR-05). The schema compatibility check (FF-03, `scripts/ff/schema_compat.py`) fails a breaking change to a model unless its `schema_version` rose and this file has an entry for the new version.

Each entry is a second-level heading naming the model and its new version, `## <Model> v<N>` (`## <Model> removed` for a removed model), followed by the upgrade step: what changed and how stored payloads of the old version are read or migrated. A change to a semantic field's default, or a move between semantic and presentation, changes what hashes mean, so its entry also has a paragraph starting `**Stored hashes.**` that says how hashes already stored are treated.

No entries yet.

## Workflow changes

DBOS recovers a workflow by replaying it against its recorded steps, and only on a control plane of the same application version, `WORKFLOW_VERSION` in `grindstone.store` (SPEC-02, DEC-0204). The workflow-version check (`scripts/ff/workflow_versions.py`) fingerprints every registered workflow and the steps it calls by name into `packages/grindstone/workflow-versions.json`, and fails when a fingerprint changes, or a workflow is removed, while `WORKFLOW_VERSION` stays the same, unless this file has an entry for the change.

A change is replay-compatible when steps were only added after every existing step, none removed or reordered. Record it in this file as a second-level heading naming the workflow and the first 12 hex digits of its new fingerprint, `## Workflow <name> <fingerprint>` (`## Workflow <name> removed` for a removed workflow), followed by why replay is safe. Any other change raises `WORKFLOW_VERSION`; workflows in flight under the old version are then drained on the previous image or moved with `grindstone workflows fork <id>`.

No workflow entries yet.
