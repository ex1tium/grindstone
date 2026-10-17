"""Export the JSON Schema bundle of every exported contract (ADR-05, FF-02).

Writes `packages/contracts-ts/schemas/contracts.schema.json`: one schema with
every model in `grindstone.contracts.EXPORTED` under `$defs`, so shared
definitions appear once. `scripts/gen-contracts-ts.mjs` turns it into
TypeScript. CI regenerates both and fails on any diff.
"""

import json
from pathlib import Path

from grindstone.contracts import EXPORTED, bundle_schema

OUT = Path(__file__).resolve().parents[1] / "packages" / "contracts-ts" / "schemas"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    bundle = bundle_schema(EXPORTED, title="GrindstoneContracts")
    text = json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    target = OUT / "contracts.schema.json"
    target.write_text(text)
    for stale in OUT.glob("*.json"):
        if stale != target:
            stale.unlink()


if __name__ == "__main__":
    main()
