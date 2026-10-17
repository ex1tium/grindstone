# SPEC-01 review 1

Reviewer: a session that did not write SPEC-01 (17 October 2026). Reviewed against the Planning playbook's validation checklist and the foundation v4.5 text, with each factual claim checked against the code and primary sources.

**Verdict: changes required.** Three blocking findings (F1, F2, F3); six minor ones. The design is otherwise sound and compact, and the scope, ownership and test plan are right for the walking skeleton.

## Blocking

**F1. The item ID grammar refuses ID forms the foundation defines.** REQ-0109 and the `ItemId` pattern `^[A-Z][A-Z0-9]{0,7}-[0-9]+(-[0-9]+)?$` refuse `PRD` (`sdlc.product`) and `M1` (`sdlc.milestone`), both defined in the Factories tab ("Item kinds and artifacts"). And `sdlc.exit_criterion` IDs (`M1-01`, `M2-03`) have no prefix fixed by the kind, which REQ-0109 assumes: `item_id_type("M")` cannot express "M, a milestone number, a hyphen, a sequence". Checked: `PRD` and `M1` fail the pattern; every other form in the foundation passes.
*Fix:* a kind declares its ID pattern when it registers (SPEC-03's registry), and `item_id_type` takes that declaration rather than a bare prefix. The base `ItemId` grammar must admit every declared form (for example `^[A-Z][A-Z0-9]{0,7}(-[0-9]+){0,2}$`, which admits `PRD`, `M1`, `M1-01`, `AC-0101-1`). Add the foundation's forms to AC-0109-1.

**F2. A set in semantic content hashes differently in different processes.** REQ-0106 admits lists; Pydantic serializes `set` and `frozenset` fields as lists in iteration order, and string hashing is randomized per process. Checked with Pydantic as locked here: `frozenset({'alpha','beta','gamma','delta'})` serializes as `['beta','delta','gamma','alpha']`, `['delta','gamma','alpha','beta']` and `['gamma','beta','delta','alpha']` under `PYTHONHASHSEED` 1, 2 and 3. The same content would therefore have a different semantic hash on every restart, and evidence would look stale at random.
*Fix:* refuse `set` and `frozenset` (and any other unordered collection) in semantic content at class definition, as REQ-0106 does for floats, and say so in REQ-0106; contracts that mean a set use a tuple sorted and de-duplicated by a validator, as `RunManifest.items` already does. Add a golden vector and a property test that hashes the same instance in subprocesses with different `PYTHONHASHSEED` values.

**F3. The proposed record must be in the foundation, and accepted, before TKT-0103.** Section 6 proposes that semantic hashes omit defaulted fields, render as `sha256:<hex>`, and treat a changed semantic default as breaking. The glossary ("Hash"), ADR-08 and the Components tab ("Hashing contract") define the hash without that refinement, so the change needs a record. The reviewer has carried the proposal, as written in SPEC-01, into the foundation as **ADR-44** in v4.5, next to ADR-42 and ADR-43; the operator accepted all three on 17 October 2026. SPEC-01 should cite ADR-44.

## Minor

**F4. NFC normalisation of keys can create duplicate keys.** Two keys that differ only in normalisation (`"é"` precomposed and decomposed) become the same key after step 4, and RFC 8785 has no answer for duplicate keys. Refuse an object whose keys collide after NFC (a validation error), and add a golden vector.

**F5. Blob hashes and `blob_set` versions are not fully specified.** `BlobRef.sha256` has no stated rendering; use the same `sha256:<hex>` form as DEC-0104, so every hash in the system reads the same. "The hash of the sorted member hashes" for `blob_set` should be defined exactly, for example the semantic hash of the sorted tuple of member `BlobRef`s.

**F6. `git_commit` accepts only 40 hex digits.** Git repositories in SHA-256 object format use 64; accept 40 or 64 now rather than migrate a contract later.

**F7. Examples name factory kinds (checklist item 19).** AC-0109-1 uses `REQ-` and `TKT-`, SDLC prefixes. A kernel specification's examples use the `notes` factory (`N-3`) or kernel kinds (`P-`, `FND-`). The specification's own requirement and criterion IDs (`REQ-0101`, `AC-0101-1`) are its ID block and are fine.

**F8. ADR-11 is cited in the purpose and touched by the proposed record, but missing from "Foundation links".** Add it: the semantic hash is what ADR-11's freshness compares.

**F9. One wording gap.** REQ-0101 says `Contract` "marks every defaulted field as required in serialization schemas", while REQ-0107 omits defaults from the hash; both are right, but one sentence in section 5 should say that the serialized form always carries every field and only the canonical hash form omits defaults, so readers do not take one for the other.

## Facts checked

| Claim | Source | Result |
| --- | --- | --- |
| `rfc8785` 0.1.4 is the latest | PyPI JSON API, 17 October 2026 | 0.1.4, released 2024-09-27: latest |
| `canonicalize` 5.1.0 is the latest | npm registry, 17 October 2026 | 5.1.0, released 2026-09-18, Apache-2.0: latest |
| `uuid.uuid7()` is in the Python 3.14 standard library | Python 3.14 (pinned 3.14.8) | yes |
| The six error classes and their codes | Foundation, "Error model and configuration" | match |
| `test_field_titles_are_dropped_and_defaults_are_required` and `test_schema_bundle_matches_contracts` exist | `tests/fitness/test_ff02_contract_drift.py` | both exist |
| The spec map assigns M1-06 to SPEC-01 (shared with SPEC-06) | Roadmap, spec map | yes; SPEC-01 claims only the contract clause |

## Checklist

| # | Item | Result |
| --- | --- | --- |
| 1 | Every template section present; no unbounded TBD | pass |
| 2 | Requirements testable, stable IDs | pass |
| 3 | Every AC names requirement, method, test; every requirement has one | pass |
| 4 | Assigned exit criteria mapped; nothing claimed from others | pass (M1-06 contract clause) |
| 5 | Invariants, scenarios and records cited; no contradiction | **fail**: F1 (Factories tab ID forms), F3 (hashing contract), F8 |
| 6 | Dependencies earlier or own milestone, acyclic, module map | pass (none) |
| 7 | No state or key owned twice | pass |
| 8 | Idempotency for external actions | n/a: no effects |
| 9 | Boundaries typed, schema versions, generated artifacts named | pass |
| 10 | Migration and upgrade path | pass (no stored data before M1; `docs/upgrades.md` starts) |
| 11 | Trust boundaries | pass (a hash is not a signature, stated) |
| 12 | Derivable values computed, not stored | pass (`blob_set` version derived) |
| 13 | Dependencies with reason and pinned version from a primary source | pass (checked above) |
| 14 | Cross-module choices as decision records | pass once F3 is accepted |
| 15 | Typed errors, none swallowed | pass |
| 16 | Test plan kinds | **fail**: F2 needs a cross-process property test |
| 17 | Terms match the glossary | pass |
| 18 | Reviewable in one sitting | pass |
| 19 | Kernel spec names no factory kind | **fail**: F7 |
| 20 | Factory 5F | n/a: kernel specification |
| 21 | Maker and prover differ | pass (stated) |
| 22 | Cooperation | n/a |
| 23 | Irreversible actions | n/a |
| 24 | Fitness functions added or extended | pass (FF-02 extended, FF-03 added) |

## Next

The author's revision addresses F1, F2 and F4–F9 in the specification, and cites ADR-44. Then the operator decides ADR-44 with ADR-42 and ADR-43, and approves SPEC-01.

## Revision 1 (17 October 2026)

By the operator's instruction, the reviewing session also made the revision; the playbook's separation of author and reviewer is therefore not met for these changes, and the M0 review session confirms that each finding is closed before the operator approves SPEC-01.

| Finding | Change in SPEC-01 |
| --- | --- |
| F1 | REQ-0109 restated: one base grammar `^[A-Z][A-Z0-9]{0,7}(-[0-9]+){0,2}$` admitting `PRD`, `M1`, `M1-01`, `N-3`, `AC-0101-1`; each kind declares an anchored pattern with example IDs when it registers (SPEC-03); typed IDs validate the base grammar, then the kind's pattern. AC-0109-1 rewritten to match. |
| F2 | REQ-0106 refuses `set` and `frozenset` in semantic content at class definition; the design explains why and points to sorted tuples. AC-0106-2 (refusal) and AC-0106-3 (hash identical across `PYTHONHASHSEED` values in subprocesses) added. |
| F3 | Accepted as ADR-44; section 3 cites ADR-08 as amended by ADR-44; section 6 records the acceptance; TKT-0103 no longer waits on it. |
| F4 | REQ-0105 refuses keys that collide after NFC; canonical-form step 4 says so; AC-0105-2 added. |
| F5 | `BlobRef.sha256` is written `sha256:<hex>`; a `blob_set`'s version is the semantic hash of its sorted `members` tuple; REQ-0115 and AC-0115-1 added. |
| F6 | `git_commit` accepts 40 or 64 lowercase hex (REQ-0115, AC-0115-1). |
| F7 | AC-0109-1 uses neutral examples and the `notes` factory's `N-` IDs instead of SDLC prefixes. |
| F8 | ADR-11 added to section 3. |
| F9 | Section 5 states that the serialized form always carries every field and only the canonical form for hashing omits defaults. |

The golden vectors also gain every control character U+0000–U+001F, which OQ-0101 already named as its default.
