# SPEC-01 review 2

Reviewer: a session that wrote none of SPEC-01 to SPEC-10 (17 October 2026). It checks revision 1 against the nine findings of review 1 (`SPEC-01-review-1.md`). Review 1's reviewer also made revision 1, so this check stands in for an independent review of the revision. Facts were checked against the foundation v4.5 text, the repository and PyPI.

**Verdict: every review 1 finding is closed. Approve after the minor changes below.** None of them blocks approval, but N3 should land before TKT-0103 is implemented, because it changes what the hash function accepts.

## Review 1 findings

| Finding | Closed? | Evidence in revision 1 |
| --- | --- | --- |
| F1 ID grammar | Yes | The base grammar `^[A-Z][A-Z0-9]{0,7}(-[0-9]+){0,2}$` admits every ID form the foundation defines: `PRD`, `M1`, `M1-01`, `FEAT-n`, `SPEC-nn`, `REQ-nnxx`, `AC-nnxx-k`, `TKT-nnnn`, `ADR-nn`, `P-n`, `LRN-n`, `FND-n`, `OBS-n`, `IF-n`. A kind declares an anchored pattern and example IDs (SPEC-03's `KindDecl.id`, checked by its loader). AC-0109-1 tests the grammar, the kind pattern and the example check. |
| F2 Unordered collections | Yes | REQ-0106 refuses `set` and `frozenset` at class definition. AC-0106-2 tests the refusal, and AC-0106-3 tests stability across `PYTHONHASHSEED` values in subprocesses. The design points to sorted, de-duplicated tuples. |
| F3 Record before TKT-0103 | Yes | ADR-44 is in the foundation, accepted. Section 3 cites "ADR-08 as amended by ADR-44", section 6 records the acceptance, and TKT-0103 no longer waits on it. |
| F4 NFC key collisions | Yes, with residual N2 | REQ-0105, canonical-form step 4 and AC-0105-2. |
| F5 Blob hash form, `blob_set` version | Yes, with residual N1 | `BlobRef.sha256` is written `sha256:<hex>`; REQ-0115 and AC-0115-1. |
| F6 SHA-256 commits | Yes | `git_commit` accepts 40 or 64 lowercase hex digits (REQ-0115, AC-0115-1). |
| F7 Factory names in examples | Yes | AC-0109-1 uses neutral IDs and the `notes` factory's `N-` IDs. `PRD` and `M1-01` appear only as examples of grammar forms, not as kind names, which checklist item 19 allows. |
| F8 ADR-11 missing | Yes | Section 3 cites it. |
| F9 Serialized versus canonical form | Yes | Section 5 says it in one sentence after the canonical-form steps. |

The diff from the reviewed draft (`5fe4576`) to revision 1 (`6bee38b`) changes only what the revision table lists, plus the control-character vectors that OQ-0101 named.

## Residual and new findings (minor)

**N1. The `blob_set` version differs from the foundation's wording and has no golden vector.** The Concepts tab ("Subjects") defines the version as "hash of the sorted member hashes". Revision 1 hashes the sorted tuple of member `BlobRef`s, which also contain `media_type` and `size`. Relabelling a member's media type would then change the version and stale evidence although no byte changed. `semantic_hash` is also defined over a contract, not a bare tuple, so AC-0115-1 cannot yet be written exactly.
*Change:* define the version as the semantic hash of the sorted tuple of member hashes (the `sha256` strings only), as the foundation says. State the function (`blob_set_version(members)`) and add a golden vector so TypeScript agrees.

**N2. Refusals are not bound across languages.** REQ-0108 binds the two implementations only on vectors that hash. A key collision after NFC (F4), a float, or an integer beyond ±(2^53 − 1) are refused in Python by AC-0105-2 and AC-0106-1, but nothing requires TypeScript to refuse them too.
*Change:* add refusal vectors (input, expected error) to `hash-vectors.json`, and extend AC-0108-1 and AC-0108-2 to them.

**N3. JSON-typed semantic fields escape the class-definition check.** REQ-0106 refuses floats and sets "when the contract class is defined". A field typed `JsonObject` or `JsonValue` can hold a float at run time, and other specifications hash such fields:
- SPEC-08's `Check.definition_hash` covers `CheckSpec.params` (JSON);
- SPEC-04's decision context hash covers payloads.

The class check must either refuse those classes, which would make `CheckSpec` impossible, or admit them, which lets a float reach the hash.
*Change:* say that `canonical_bytes` also refuses, at hash time, any float, non-safe integer or non-JSON value inside JSON-typed fields (validation class, a new code such as `hash_input_invalid`). Add a unit test and a refusal vector (N2).

**N4. TKT-0101 cannot satisfy all of AC-0115-1.** The `blob_set` clause of AC-0115-1 needs `semantic_hash`, which TKT-0103 builds, and TKT-0103 depends on TKT-0101.
*Change:* move the `blob_set` clause into its own criterion under TKT-0103, or make REQ-0115's `blob_set` part a TKT-0103 item.

**N5. The run manifest does not carry configuration hashes.** The Components tab ("Error model and configuration") says configuration "is hashed, and its hash is recorded on every run that used it (I-06)". SPEC-03 makes the instance and project configuration hashes readable "so SPEC-06 can record it". Neither `RunManifest` nor SPEC-06 records them. This is cross-cutting finding X4 of `M1-specifications-review-1.md`.
*Change:* add `instance_config_hash` and `project_config_hash` (both `SemanticHash`) to `RunManifest`, and extend AC-0110-1.

**N6. Foundation wording (for the operator, not SPEC-01).** The Concepts tab still says "Identity: A stable ID, `PREFIX-n`" and "declaring … its ID prefix". The foundation's own `PRD` and `M<n>` forms never matched that, and SPEC-01 now has kinds declare a pattern. This is an editorial alignment for the next foundation revision. It needs no record, because ADR-08 states no ID grammar.

## Checklist (revision 1)

| # | Item | Result |
| --- | --- | --- |
| 1 | Sections present; no unbounded TBD | pass |
| 2 | Requirements testable, stable IDs | pass |
| 3 | Every AC names requirement, method, test; every requirement has one | pass |
| 4 | Assigned exit criteria mapped | pass (M1-06, contract clause) |
| 5 | Invariants, scenarios, records cited; no contradiction | pass, N1 aside |
| 6 | Dependencies | pass (none) |
| 7 | Ownership | pass; see X3 in the summary for the ownership table's "revisions" row |
| 8 | Idempotency | n/a: no effects |
| 9 | Typed boundaries, schema versions, generated artifacts | pass |
| 10 | Migration and upgrade path | pass |
| 11 | Trust boundaries | pass |
| 12 | Derivable values computed | pass |
| 13 | Dependencies pinned from a primary source | pass: `rfc8785` 0.1.4 (2024-09-27) and `canonicalize` 5.1.0 (2026-09-18) are still the latest on PyPI and npm (checked 17 October 2026) |
| 14 | Cross-module choices as records | pass (ADR-44) |
| 15 | Typed errors | pass, N3 aside |
| 16 | Test plan kinds | pass, N2 aside |
| 17 | Terms | pass |
| 18 | One sitting | pass |
| 19 | Kernel names no factory kind | pass |
| 20 | Factory 5F | n/a: kernel specification |
| 21 | Maker and prover differ | pass |
| 22 | Cooperation | n/a |
| 23 | Irreversible actions | n/a |
| 24 | Fitness functions | pass (FF-02 extended, FF-03 added) |

## Next

The author applies N1 to N5. Then the operator approves SPEC-01 with the other nine specifications (`M1-specifications-review-1.md`).
