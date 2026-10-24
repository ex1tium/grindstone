# Upgrades

Upgrade steps for breaking changes to contracts (ADR-05). The schema compatibility check (FF-03, `scripts/ff/schema_compat.py`) fails a breaking change to a model unless its `schema_version` rose and this file has an entry for the new version.

Each entry is a second-level heading naming the model and its new version, `## <Model> v<N>` (`## <Model> removed` for a removed model), followed by the upgrade step: what changed and how stored payloads of the old version are read or migrated. A change to a semantic field's default, or a move between semantic and presentation, changes what hashes mean, so its entry also has a paragraph starting `**Stored hashes.**` that says how hashes already stored are treated.

No entries yet.
