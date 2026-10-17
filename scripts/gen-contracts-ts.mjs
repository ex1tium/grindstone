// Generate TypeScript types from the contract schema bundle (ADR-05, FF-02).
// Input: packages/contracts-ts/schemas/contracts.schema.json (gen_contract_schemas.py).
// Output: packages/contracts-ts/src/index.ts. Do not edit the output by hand.
import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { compile } from "json-schema-to-typescript";

const root = join(import.meta.dirname, "..", "packages", "contracts-ts");
const bundle = JSON.parse(await readFile(join(root, "schemas", "contracts.schema.json"), "utf8"));

// Reference every definition from a root object so each one is emitted once,
// named by its title; the root type maps contract names to their types.
const names = Object.keys(bundle.$defs).sort();
const root_schema = {
  $defs: bundle.$defs,
  title: "GrindstoneContracts",
  type: "object",
  additionalProperties: false,
  required: names,
  properties: Object.fromEntries(names.map((n) => [n, { $ref: `#/$defs/${n}` }])),
};
const ts = await compile(root_schema, "GrindstoneContracts", {
  bannerComment:
    "// Generated from the Pydantic contracts in grindstone.contracts. Do not edit.\n" +
    "// Regenerate with `make gen`; CI fails on drift (FF-02).",
  additionalProperties: false,
  strictIndexSignatures: true,
  format: false,
});
await writeFile(join(root, "src", "index.ts"), ts);
