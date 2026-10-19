# M1 specifications, revision 1: how each review finding was answered

Author: the session that wrote SPEC-02 to SPEC-10 and revision 1 of SPEC-01 (18 October 2026). It answers `M1-specifications-review-1.md` and the per-specification reviews. Every blocking and minor finding was accepted; where the author chose a different fix from the one the reviewer proposed, the reason is given. The confirmation pass checks the blocking rows; the author's checklist run covers the rest.

## Operator decisions (18 October 2026)

| Item | Decision | Where |
| --- | --- | --- |
| Proposed record: delivery-port operations | Accepted as ADR-45 | Foundation v4.6 |
| Proposed record: dependency currency | Accepted as ADR-46 | Foundation v4.6 |
| Ownership table (X3) | Amended as proposed | Foundation v4.6, Roadmap |
| Editorial alignments (X7) | Made | Foundation v4.6 |
| Playbook rule 6 for dependencies | Reworded as proposed | Foundation v4.6 |

## Cross-cutting findings

| Finding | Answer |
| --- | --- |
| X1 module-map violations | `work` no longer calls `change` or `delivery`, and `delivery` no longer calls `change`. **Different fix for drafts:** instead of `change` consuming `run.collected` and `delivery.bypass_observed`, which would make SPEC-04 depend on SPEC-06 and SPEC-08 (a cycle), SPEC-04 owns one event contract, `change.draft_requested`, that `work` and `delivery` emit (SPEC-04 REQ-0421, DEC-0406). `delivery` prepares from its consumer of `task.transitioned` to `delivering` (SPEC-08). `evidence` keeps each task's current subject in `task_subjects`, written by `plan_checks` (SPEC-08). |
| X2 FF-07, FF-08, FF-09 | FF-07 and FF-09 are built in SPEC-02 (REQ-0215, REQ-0216, TKT-0206), FF-08 in SPEC-04 (REQ-0420, TKT-0405), each with fixtures and an acceptance criterion. |
| X3 ownership table | Foundation v4.6. |
| X4 configuration hashes in the manifest | SPEC-01 `RunManifest` and REQ-0110; SPEC-06 part 2 REQ-0605 and AC-0605-1. |
| X5 error codes below `platform` | Kernel codes are declared in `grindstone.contracts.errors` by each kernel specification; the registry is for factory codes and copies the kernel list (SPEC-01, SPEC-03, and the wording in every specification). |
| X6 specification cycles | SPEC-06 split into part 1 (`stations`, the host) and part 2 (`work`): part 1 ← SPEC-08 ← part 2. Argon2 parameters and the `argon2-cffi` pin are SPEC-05's. Part 2 states that it defines the token-minting hook and does not depend on SPEC-07. `SubjectResolver` moved to part 1, because SPEC-08 depends on part 1. |
| X7 foundation text | Foundation v4.6. |
| X8 kernel neutrality | SPEC-02 ("a delivery adapter by its documented lookup"), SPEC-04 (factory lifecycles), SPEC-06 (`tool_timeout_seconds`, mapped by the Claude preset in SPEC-05), SPEC-08 (accepted, gate state, external change), SPEC-03 (DEC-0306 without SDLC). |
| Question 2 conditions | (a) OQ-0301 names grants and `author_kind: person`. (b) The approval card states "reject and draft a larger change" (SPEC-10). SPEC-04's F1 fixed. (c) A delivery `closed` after its task is done escalates; the stale-after-delivery path is stated (SPEC-08). |

## Per specification

**SPEC-01 (review 2):** N1 `blob_set_version` over member hashes with a golden vector (REQ-0115, AC-0115-2). N2 refusal vectors (REQ-0108, AC-0108-1, AC-0108-2). N3 JSON-typed fields checked at hash time, `hash_input_invalid` (REQ-0106, AC-0106-4). N4 the `blob_set` clause moved to TKT-0103 (AC-0115-2). N5 configuration hashes (X4). N6 foundation v4.6.

**SPEC-02:** F1 keys from the causing record's ID, carried as a workflow input, so a fork repeats no effect (REQ-0204, AC-0204-3). F2 "or by a lookup on the causing record". F3 one lease root per owner. F4 OQ-0201 and AC-0203-3 cover isolation and retry. F5 FF-07 exempts DBOS's outputs table. F6 distinct blobs in project usage. F7 (X5). F8 (X8). X2 FF-07 and FF-09 built here.

**SPEC-03 and its architecture review:** A1 contexts are a protocol in the SDK, implemented in the composition root and obtained through `platform.context_for`; factories never build one. A2 the port follows ADR-45. A3 two-phase loading to a fixed point (REQ-0318, AC-0318-1, DEC-0307). A4 one export table with owners. A5 factory storage as DEC-0306, neutral. A6 consumers are order-independent (REQ-0319, AC-0319-1). A7 no factory events in SDK 0.1.0. A8 the mode mapping is stated once. A9 needs: offer only your own or `core` needs; requesting another factory's need stays allowed. A10 manifests read through `importlib.metadata`; code imported only after phase 2. A11 extra skills deferred (OQ-0303). F1 OQ-0301 names grants. F2 `secret_not_granted`. F4 overrides name a model slot. F6 `project_status` reports paused. Also, from SPEC-06's F5: a capability whose permissions say `decision` is refused at load in M1.

**SPEC-04:** F1 a moved base never applies on the old approval; the approval is superseded and asked again with diffs against the new base (REQ-0415, AC-0415-1). F2 a factory version removing a state still held is refused. F3 allocation skips imported numbers. F4 `core.interface.contract` is text holding JSON, validated by SPEC-11 without a type change (OQ-0403). F5 foundation v4.6. F6 (X8). X1 and X2 as above.

**SPEC-05:** F1 `postgres` stated as the one exception, in FF-05 and AC-0502-1. F2 the host streams the archive to an extractor running as the agent user; AC-0506-1 checks the agent cannot open it. F3 **the runner has no network** (DEC-0505), the reviewer's recommendation. F4 shared loopback stated; AC-0511-1 extended. F5 and F6 parameters and the hashing tool (`scripts/hash_password.py`) owned here. F7 the Docker documentation is quoted; environment-sourced secrets, which Compose does give an owner and mode, are recorded as a rejected option.

**SPEC-06 (now two parts):** F1 **different fix:** a run binds one agent user from a pool of eight for its life, while lanes stay queues (part 1 REQ-0623, DEC-0606; SPEC-05 DEC-0502). Binding a run to a lane slot, as proposed, would let a run waiting on the operator hold a lane, against ADR-14. F2 runs gain `suspended` and turns an end state (part 2 REQ-0627); SPEC-07 checks the turn is open. F3 (X4). F4 agent-neutral options (part 1 REQ-0626). F5 agent permission requests denied in M1, `decision` refused at load (part 2 REQ-0614, DEC-0608). F6 the lane rule cited, now in the foundation. F7 `waiting` while collect's permission decisions are open. F8 `storage_limit` in the failure table. F9 events in order per session (part 1 REQ-0625). F10 output files read from the subject (part 2 DEC-0609). F11 the readiness thinning stated (REQ-0602).

**SPEC-07:** F1 tokens valid only while their turn is open. F2 report paths bounded by the contract. F3 DEC-0704. F4 proposal references limited to pins and same-draft items (DEC-0705), the reviewer's preference.

**SPEC-08:** F1 gate-state posts keyed by the `gate_posts` row, so `success → pending → success` posts three times (AC-0814-2). X1 as above. ADR-45 names throughout (`publish_gate_state`, `accept`, `accepted`). F2 bypass coverage stated, OQ-0803 names SPEC-24. F3 the mode is observed at project setup. F4 OQ-0802 folded into REQ-0807. F5 closed-after-done escalation and the stale path. F6 neutral wording.

**SPEC-09:** F1 collect builds the commit with `hash-object`, `update-index` and `commit-tree`, so no checkout path is opened (REQ-0912, DEC-0906, AC-0912-3). F2 the diff against the base is the collect outcome's prover context, which part 2 gives every check task (REQ-0923, part 2 REQ-0628, AC-0907-1). F3 the `proposed` state explained. F4 tickets with `manual` or `command` criteria are refused by `/implement` (AC-0904-2). F5 DEC-0905. F6 the SDK export table. F7 the reading is recorded (DEC-0907), the reviewer's preference. F8 bypass coverage stated. OQ-0901 updated for the runner's lack of network.

**SPEC-10:** F1 Argon2 cited from SPEC-05. F2 limit codes 409, login 429. F3 `X-Grindstone-Client: web`. F4 the `operators` table noted for SPEC-22 or SPEC-26. F5 ADR-46 cited.

## Next

A confirmation pass, by a session that did not write the specifications, on the blocking findings: X1, X2, SPEC-02 F1, SPEC-04 F1, SPEC-06 F1 to F3 (with the different fix for F1), SPEC-08 F1, SPEC-09 F1 and F2, and A1 to A3. Then the operator approves the ten.
