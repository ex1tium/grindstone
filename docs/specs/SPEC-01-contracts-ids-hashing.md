# SPEC-01 — Contracts, IDs, hashing and code generation
Status: draft · Milestone: M1
Kind: kernel · Owns: `grindstone.contracts` (base contract, typed IDs, references, provenance, run manifest, error envelope, semantic hashing, schema generation, schema compatibility check)

Compact walking-skeleton specification (Planning playbook). Review: by a session that did not write it, then the operator.

## 1. Purpose

Every record, report, event and payload in Grindstone is a Pydantic contract (ADR-05), and every claim of freshness rests on one semantic hash computed the same way in Python and TypeScript (ADR-08, ADR-11). This specification fixes the base contract, the typed identifiers and references every module passes around, the provenance every revision carries (I-02), the run manifest every task run records (I-06, M1-06), the typed error envelope, and the hashing and code generation everything else trusts. Later specifications add models; none redefines these.

## 2. Scope

In scope:
- The `Contract` base class and its configuration, and the `schema_version` rule.
- Typed item IDs (`PREFIX-n`) and record IDs (UUIDv7).
- Reference contracts: `ItemRef`, `BlobRef`, `SubjectRef`.
- `Provenance` and `RunManifest`.
- The error envelope and the six error classes (Components tab, "Error model and configuration").
- Semantic and presentation fields; `semantic_hash()`; golden vectors run by Python and TypeScript.
- The JSON Schema bundle and TypeScript generation (FF-02), and the schema compatibility check (FF-03).

Out of scope:
- Item kinds, artifacts, edges and the revision tables: SPEC-04 (thin, M1), then SPEC-11 (M2).
- Lifecycle definitions and their generated SQL enums: SPEC-04, which adds the SQL generator to the code-generation step defined here.
- The event union and outbox: SPEC-03.
- The OpenAPI document: SPEC-10.
- Writing run manifests: SPEC-06. This specification defines the contract; SPEC-06 records it before a session opens.
- Freshness itself: SPEC-08 (M1, thin), then SPEC-12 (M2). This specification supplies the hashes it compares.

## 3. Foundation links

Implements:
- ADR-05: Pydantic is the only hand-written source of types; everything else is generated and drift-checked; stored payloads carry a schema version.
- ADR-08: namespaced kinds with stable typed IDs; semantic hashes over RFC 8785 canonical JSON after NFC and LF normalisation. This specification makes the canonical form precise (section 5) and proposes one refinement as a decision record (section 6).
- I-02: the provenance contract every revision carries.
- I-06: the run manifest names everything a run used.
- I-05, QS-02: semantic hashes are what freshness compares, so a presentation edit must never change one, and a semantic edit always must.

Delivers:
- M1-06, the contract clause: every field the run record names has a typed contract and a stable hash → AC-0110-1, AC-0110-2. SPEC-06 delivers the recording clause.

Depends on: none.

Scenarios: K1 steps 2, 5 and 6 rely on `ItemRef` hashes, `BlobRef` and the run manifest.

## 4. Requirements

REQ-0101: Every model in `grindstone.contracts` derives from `Contract`, which is immutable, rejects unknown fields, and marks every defaulted field as required in serialization schemas.
REQ-0102: Every contract that is stored, sent between processes or exposed to clients has a `schema_version` field typed as a literal integer.
REQ-0103: `semantic_hash(contract)` returns `sha256:` followed by 64 lowercase hex digits, computed over the RFC 8785 canonical JSON of the contract's semantic content, defined in section 5.
REQ-0104: A field is semantic unless it is explicitly marked presentation; changing only presentation fields never changes the semantic hash, and changing any semantic field always does.
REQ-0105: Every string in semantic content, keys and values, is normalised to Unicode NFC, and every line ending to LF, before canonicalisation.
REQ-0106: Semantic content admits only strings, booleans, null, integers within ±(2^53 − 1), lists and objects; a contract whose semantic fields can hold a float is refused when the contract class is defined.
REQ-0107: A semantic field whose value equals its declared default is omitted from the canonical form, so adding an optional, defaulted field to a contract leaves every existing hash unchanged (proposed record, section 6).
REQ-0108: Golden vectors (input, canonical bytes, hash) live in `grindstone.contracts`, and the Python and TypeScript implementations both reproduce every vector exactly.
REQ-0109: Item IDs are typed per kind as `PREFIX-n`, with the prefix fixed by the kind; parsing an ID of the wrong prefix for its type fails validation.
REQ-0110: The `RunManifest` contract holds the pinned item revisions, capability hash, factory version, provider, model, subject version, context pack hash and prompt blobs of one run, and has a stable semantic hash.
REQ-0111: Record IDs are UUIDv7, typed per record kind.
REQ-0112: Every service error is an `ErrorEnvelope` with a stable code from a closed set per class, a message for people, a structured detail, and whether a retry can help.
REQ-0113: `make gen` regenerates the JSON Schema bundle and the TypeScript types deterministically, and CI fails on any difference from the committed files (FF-02).
REQ-0114: CI classifies every change to the schema bundle against the base branch as compatible or breaking, and fails a breaking change unless the affected model's `schema_version` was raised and an upgrade note names it (FF-03).

## 5. Design

**Contracts.** Modules in `grindstone.contracts`: `base` (`Contract`, the schema bundle), `ids`, `refs`, `provenance`, `run`, `errors`, `hashing`, `health`. Everything public is re-exported from the package; `EXPORTED` lists the models generated for TypeScript.

| Model | Fields | Schema version |
| --- | --- | --- |
| `ItemRef` | `id: ItemId`, `hash: SemanticHash` | 1 |
| `BlobRef` | `sha256: BlobHash`, `media_type: str`, `size: int` (≥ 0) | 1 |
| `SubjectRef` | Discriminated union on `kind`: `git_commit` (`repo: str`, `sha: str`, 40 hex), `blob` (`blob: BlobRef`), `blob_set` (`members: tuple[BlobRef, ...]`, sorted and unique by hash; its version is the hash of the sorted member hashes), `item_revision` (`item: ItemRef`). Factory subject kinds reduce to one of these (Concepts, "Subjects") and arrive through the registry in SPEC-03 | 1 |
| `Provenance` | `author_kind: person \| agent \| policy \| system`, `author: str`, `changeset: ChangeSetId \| None`, `task: TaskId \| None`, `finding: ItemId \| None`, `decision: DecisionId \| None`, `reason: str` (non-empty) | 1 |
| `RunManifest` | `run: RunId`, `task: TaskId`, `items: tuple[ItemRef, ...]` (sorted by ID and unique, enforced by a validator, so equal manifests hash equally), `capability: str`, `capability_hash: SemanticHash`, `factory: str`, `factory_version: str`, `provider: str`, `model: str`, `subject: SubjectRef \| None`, `context_pack_hash: SemanticHash`, `prompts: tuple[BlobRef, ...]` | 1 |
| `ErrorEnvelope` | `code: str`, `error_class: validation \| rule \| authority \| limit \| transient \| internal`, `message: str`, `detail: JsonObject`, `retryable: bool` | 1 |

`ErrorEnvelope.code` is validated against a registry of codes per class: kernel codes are declared here, starting with the codes the Components tab names; later specifications register more through SPEC-03's registry, and an unregistered code is refused.

**Identifiers.** `ItemId` is a constrained string `^[A-Z][A-Z0-9]{0,7}-[0-9]+(-[0-9]+)?$`. `item_id_type("REQ")` returns a distinct annotated type that also checks the prefix, so a `ReqId` field refuses `TKT-0001`; criterion IDs (`AC-0101-1`) use the optional second number. IDs are compared as strings and never reused; allocating them is `intent`'s job (SPEC-04). Record IDs (`RunId`, `TaskId`, `ChangeSetId`, `DecisionId`, …) are `NewType`s over `uuid.UUID`, version 7, created with the standard library's `uuid.uuid7()`. Python 3.14 is the first version with it in the standard library (`docs/m0/versions.md`).

**Semantic and presentation fields.** A field is marked presentation with `Annotated[T, Presentation]`. Everything unmarked is semantic: an unmarked field makes evidence stale too often, never too rarely. At class definition, `Contract.__pydantic_init_subclass__` computes and caches the semantic field set, recursing into nested contracts, and refuses a float anywhere in semantic content (REQ-0106). Lifecycle state is never a contract field of an item: it is stored beside the item (Concepts, "Lifecycles").

**Canonical form and hash.**
1. Take the semantic fields; recurse into nested contracts, applying each one's own semantic set.
2. Omit any field whose value equals its declared default (REQ-0107).
3. Serialise to JSON values (Pydantic JSON mode): enums by value, UUIDs and dates as strings.
4. Normalise every string, keys included, to NFC, and `\r\n` and lone `\r` to `\n`.
5. Canonicalise with RFC 8785 (key order by UTF-16 code units, no insignificant whitespace, the RFC's string escaping).
6. Hash the UTF-8 bytes with SHA-256 and render the result as `sha256:<hex>`.

The same steps run in TypeScript (`@grindstone/contracts`, a hand-written `hashing.ts` beside the generated types), so the agent host and the UI can verify hashes. Golden vectors in `contracts/golden/hash-vectors.json` cover:
- key ordering with non-ASCII and astral-plane keys;
- NFC versus NFD input, and CRLF versus LF;
- integers at the ±(2^53 − 1) bounds;
- empty containers;
- omitted defaults;
- a presentation field ignored;
- a nested contract.

**Code generation.** As built in M0: `scripts/gen_contract_schemas.py` writes one bundle with every exported model under `$defs`, in serialization mode and without field titles. `scripts/gen-contracts-ts.mjs` compiles it to `packages/contracts-ts/src/index.ts`. SPEC-04 adds SQL enum generation to the same `make gen`.

**Schema compatibility (FF-03).** `scripts/ff/schema_compat.py` diffs the committed bundle against the base branch's, per model.

| Change | Class |
| --- | --- |
| A new model; a new optional or defaulted field; a new enum member | Compatible |
| A field removed or renamed; a type narrowed or changed; a field made required; an enum member removed; a semantic field's default changed; a field moved between semantic and presentation | Breaking |

A breaking change passes only if that model's `schema_version` literal rose and `docs/upgrades.md` has an entry naming the model and version. A change to a semantic default, or between semantic and presentation, changes what hashes mean, so its entry must say how stored hashes are treated.

**State and ownership.** No tables. `contracts` imports nothing else in `grindstone` (FF-01).

**Behaviour.** Pure functions; no external effects, so no idempotency keys.

**Interfaces.** Python: `Contract`, `Presentation`, `semantic_hash()`, `canonical_bytes()`, `item_id_type()`, the reference, provenance, run and error models, `bundle_schema()`. TypeScript: generated types, `semanticHash()` and `canonicalBytes()`.

**Configuration.** None.

**Security.** A semantic hash identifies content; it is not a signature and proves nothing about who wrote it. Integrity of records comes from the store being written only by the control plane (I-09). NFC normalisation means two strings that render identically hash identically.

**Make and prove.** This specification produces no subjects; its code is made and proven like any code: the implementer writes it, and CI and a reviewer who did not write it prove it.

**Fitness functions.** FF-02 is extended: Python and TypeScript must both reproduce the golden vectors. FF-03 is added (`make ff`), with fixtures proving that a removed field without a version bump fails and that an added optional field passes.

## 6. Decisions

DEC-0101: An unmarked field is semantic · Being wrong in that direction costs a re-check; being wrong the other way lets stale evidence count as fresh (QG-1) · Rejected: semantic by explicit mark (one forgotten mark silently weakens freshness).
DEC-0102: Floats are refused in semantic content, and integers are limited to ±(2^53 − 1) · Floating-point formatting is the one part of RFC 8785 that implementations commonly get wrong, nothing in the kernel needs floats in intent (quantities are integers in a stated unit, or decimal strings), and JavaScript represents exactly only integers in that range · Rejected: allow floats and trust both libraries (a cross-language hash mismatch makes every evidence record look stale).
DEC-0103: Use the `rfc8785` package for Python (Trail of Bits, pure Python, 0.1.4) and `canonicalize` for TypeScript (5.1.0, by an author of RFC 8785), each pinned exactly · The golden vectors bind both, so either can be replaced without changing a hash · Rejected: our own canonicaliser (UTF-16 key ordering and escaping are easy to get subtly wrong; the dependencies are small and fixed to a finished RFC).
DEC-0104: Hashes are rendered `sha256:<hex>` · The algorithm travels with the value, so a later scheme can coexist without ambiguity · Rejected: bare hex (an algorithm change would need a format migration everywhere).

**Proposed record: semantic hashes omit defaulted fields.** The foundation defines the hash as SHA-256 over the canonical JSON of the semantic fields. Read literally, adding an optional field with a default to a kind adds `"field": null` to every item's canonical form. That changes every hash and makes every piece of evidence in every project stale on an ordinary, compatible upgrade, the opposite of what the compatible-change rule promises. The proposed record refines the hashing contract:
- a semantic field whose value equals its declared default is omitted from the canonical form;
- changing a semantic field's default is a breaking change under FF-03;
- the hash is rendered with its algorithm prefix (DEC-0104).

It touches ADR-05, ADR-08 and ADR-11 and the hashing contract in the Components tab. It must be accepted before TKT-0103 is implemented.

## 7. Tickets and acceptance criteria

TKT-0101: Contract base, typed IDs, references, provenance, run manifest · implements REQ-0101, REQ-0102, REQ-0109, REQ-0110, REQ-0111 · depends on — · paths `packages/grindstone/src/grindstone/contracts/`, `packages/grindstone/tests/contracts/`.
TKT-0102: Error envelope and kernel error codes · implements REQ-0112 · depends on TKT-0101 · same paths.
TKT-0103: Canonical form, semantic hash and golden vectors in Python · implements REQ-0103 to REQ-0108 · depends on TKT-0101 and the proposed record · same paths plus `pyproject.toml` (rfc8785).
TKT-0104: TypeScript hashing against the golden vectors · implements REQ-0108 · depends on TKT-0103 · paths `packages/contracts-ts/`.
TKT-0105: FF-03 schema compatibility check · implements REQ-0114 · depends on TKT-0101 · paths `scripts/ff/`, `tests/fitness/`, `docs/upgrades.md`, `Makefile`, `.github/workflows/ci.yml`.

AC-0101-1: A contract instance cannot be mutated, and constructing one with an unknown field fails · verifies REQ-0101 · unit · `test_contract_is_frozen_and_closed`.
AC-0101-2: In the generated bundle, every defaulted field of every exported model is required · verifies REQ-0101 · unit · `test_field_titles_are_dropped_and_defaults_are_required` (exists).
AC-0102-1: Every exported model that is stored or sent has a literal-integer `schema_version` · verifies REQ-0102 · unit · `test_exported_models_have_schema_version`.
AC-0103-1: `semantic_hash` returns `sha256:` and 64 lowercase hex digits, and equals SHA-256 of `canonical_bytes` · verifies REQ-0103 · property · `test_hash_format_and_definition`.
AC-0104-1: For generated contract instances, changing only presentation fields keeps the hash, and changing any semantic field changes it · verifies REQ-0104 · property · `test_presentation_edits_never_change_hash`.
AC-0105-1: NFD and NFC spellings, and CRLF and LF text, of the same content hash identically · verifies REQ-0105 · property · `test_normalisation_before_hashing`.
AC-0106-1: Defining a contract with a float in a semantic field raises at class creation, and an integer beyond ±(2^53 − 1) is refused at validation · verifies REQ-0106 · unit · `test_floats_and_unsafe_integers_refused`.
AC-0107-1: Adding an optional defaulted field to a model leaves the hash of an instance that does not set it unchanged · verifies REQ-0107 · unit · `test_added_default_field_keeps_hashes`.
AC-0108-1: Python reproduces every golden vector's canonical bytes and hash · verifies REQ-0108 · golden round-trip · `test_python_golden_vectors`.
AC-0108-2: TypeScript reproduces every golden vector's canonical bytes and hash · verifies REQ-0108 · golden round-trip · `hash-vectors.test.ts`.
AC-0109-1: `item_id_type("REQ")` accepts `REQ-0412`, and refuses `TKT-0412`, `req-0412` and `REQ-` · verifies REQ-0109 · unit · `test_typed_item_ids`.
AC-0110-1: A `RunManifest` holds every field M1-06 names, and round-trips through JSON unchanged · verifies REQ-0110 · unit · `test_run_manifest_fields_and_round_trip`.
AC-0110-2: Two manifests that differ only in the order their items were supplied hash identically, because items are stored sorted by ID · verifies REQ-0110 · unit · `test_run_manifest_hash_is_order_independent`.
AC-0111-1: Generated record IDs are UUIDv7 and sort by creation time · verifies REQ-0111 · unit · `test_record_ids_are_uuid7`.
AC-0112-1: An `ErrorEnvelope` with a code not registered for its class is refused; every class in the error model exists · verifies REQ-0112 · unit · `test_error_codes_are_closed`.
AC-0113-1: `make ff` fails when a contract changes without `make gen` · verifies REQ-0113 · contract · `test_schema_bundle_matches_contracts` (exists).
AC-0114-1: Removing a field without raising `schema_version` fails FF-03, and adding an optional field passes · verifies REQ-0114 · contract · `test_ff03_breaking_change_needs_version_bump`.

## 8. Test plan

- Unit: AC-0101-1, AC-0102-1, AC-0106-1, AC-0107-1, AC-0109-1, AC-0110-1, AC-0110-2, AC-0111-1, AC-0112-1.
- Property, with Hypothesis strategies built from the contract classes: AC-0103-1, AC-0104-1, AC-0105-1.
- Golden round-trip: AC-0108-1 and AC-0108-2.
- Contract (FF-02, FF-03 with fixtures): AC-0101-2, AC-0113-1, AC-0114-1.

There are no crash-and-resume, integration or live-run tests: the module has no effects.

## 9. Open items and risks

OQ-0101: Does the `rfc8785` package's string escaping match `canonicalize` for every control character? · Default: the golden vectors include all of U+0000–U+001F; a mismatch is fixed by a thin wrapper on whichever side diverges · Resolved by TKT-0104.
OQ-0102: Should a factory be able to mark fields of a kernel kind it extends as presentation? · Default: no; extensions add fields only, and their semantic or presentation mark is the extension's own (I-18) · Resolved by SPEC-11.

Risks mitigated: hash drift between implementations (golden vectors); evidence going stale on a compatible upgrade (omitted defaults); silent incompatible schema changes (FF-03).
Risk added: a contributor marks a field presentation that should be semantic. Mitigation: FF-03 treats moving a field between the two as breaking, and review checks every `Presentation` mark.

## 10. Rollout

There is no stored data before M1, so no migration. From this specification on, every stored payload carries `schema_version`, and `docs/upgrades.md` starts empty. The TypeScript package stays private to the workspace.
