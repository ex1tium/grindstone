# M1 specifications, review 1: summary, cross-cutting findings and the author's questions

Reviewer: a session that wrote none of SPEC-01 to SPEC-10 (17 October 2026). This is the one-pass review the Planning playbook allows for the ten walking-skeleton specifications.

What it covers:
- SPEC-01 revision 1 against review 1;
- SPEC-02 to SPEC-10 against the validation checklist;
- the independent architecture review of SPEC-03, including the SDK ports that SPEC-06 and SPEC-08 define;
- the points `docs/m0/status.md` asked the reviewer to judge.

Every claim was checked against the foundation v4.5 text, the module map in `scripts/ff/module_map.py`, the M0 code and compose file, and the PyPI and npm registries.

The specifications are not revised here. Each file below lists the changes its author should make.

## Files

| File | Verdict |
| --- | --- |
| `SPEC-01-review-2.md` | Review 1 closed; approve after minor changes |
| `SPEC-02-review-1.md` | Changes required (1 blocking) |
| `SPEC-03-review-1.md` | Changes required (blocking findings are in the architecture review) |
| `SPEC-03-architecture-review-1.md` | Changes required (3 blocking) |
| `SPEC-04-review-1.md` | Changes required (1 blocking) |
| `SPEC-05-review-1.md` | Approve after minor changes |
| `SPEC-06-review-1.md` | Changes required (4 blocking) |
| `SPEC-07-review-1.md` | Approve after minor changes |
| `SPEC-08-review-1.md` | Changes required (2 blocking, plus the delivery-port record) |
| `SPEC-09-review-1.md` | Changes required (2 blocking) |
| `SPEC-10-review-1.md` | Approve after minor changes |

The design is sound overall. The ten specifications fit together, every M1 exit criterion maps to acceptance criteria in the specifications the spec map assigns, and no assigned clause is left unclaimed. The spike results are carried in faithfully. The blocking findings fall into four groups:
- module-map violations that FF-01 would reject at implementation (X1);
- three fitness functions that no ticket builds (X2);
- concrete defects:
  - idempotency keys under `fork` (SPEC-02);
  - a lost update on a moved base (SPEC-04);
  - workspaces and lane slots (SPEC-06);
  - a status-post key (SPEC-08);
  - a symlink escape and a reviewer who cannot see the base (SPEC-09);
- the SDK surface, which must be right at 0.1.0 because the kernel-stability measure allows no breaking SDK change after M2 (architecture review).

## Cross-cutting findings

**X1. Four module-map violations (blocking).** `scripts/ff/module_map.py` allows `work` to use `intent`, `evidence`, `decisions`, `stations` and `memory`; `delivery` to use `evidence` and `decisions`; and `evidence` to use `intent` and `stations` (each also the substrate). The designs make these calls, which FF-01 refuses:

| Call | Where | Why it is refused |
| --- | --- | --- |
| `work` → `change.draft` | SPEC-06, collect step 3 (REQ-0615) | `change` is not in `work`'s list |
| `work` → `delivery.prepare(task)` | SPEC-08, "Delivering" step 1; SPEC-06 depends on "the delivery port" | `delivery` is not in `work`'s list |
| `delivery` → `change.draft` | SPEC-08, bypass intake (REQ-0816); SPEC-08 depends on SPEC-04 for "ChangeDrafts for intake" | `change` is not in `delivery`'s list |
| `evidence` reads the task's current subject | SPEC-08, freshness | Tasks belong to `work`, above `evidence` |

*Change:* use the dependency inversion the Components tab prescribes ("a registered continuation or an event the higher module subscribes to"). Proposed:
- `work` emits `run.collected`, carrying the proposals as a blob reference; `change` consumes it and drafts.
- `work` emits `task.transitioned` to `delivering` with the task's target and subject; `delivery` consumes it and prepares.
- `delivery` emits `delivery.bypass_observed`; `change` consumes it and drafts the `untrusted` ChangeSet.
- `evidence` keeps its own record of each task's current subject. `plan_checks` writes it each time `work` plans checks for a new subject, so freshness reads only `evidence` and `intent`.

The alternative, widening the module map, changes the module map and therefore needs a record and an architecture review. The inversions above are cheaper and keep the layering.

**X2. FF-07, FF-08 and FF-09 are built by no ticket (blocking, checklist item 24).** The foundation lists all three "from M1". No such test exists in `tests/fitness/` today. SPEC-02, SPEC-03, SPEC-04, SPEC-06, SPEC-08 and SPEC-10 each say their schemas are "covered" by them, or "extend" them, but no specification adds them and no ticket or acceptance criterion builds them. AC-0402-1 and SPEC-08's two-doors rule depend on FF-08 existing.
*Change:* SPEC-02 adds FF-07 (SQL and migrations touch only the module's schema) and FF-09 (no column named in a deny-list of derived values). SPEC-04 adds FF-08 (lifecycle columns written only by their registered transition function), each with a ticket, fixtures and an acceptance criterion. The other specifications keep their "covers" lines.

**X3. The Roadmap's ownership table disagrees with four claims (operator).** Each claim is reasonable, but the playbook says the ownership table decides, so the table should be amended:

| Row | Table says | Specifications do | Proposed row |
| --- | --- | --- | --- |
| Contracts, typed IDs, hashing, revisions | Introduced by SPEC-01 | SPEC-01 defines `Provenance`; SPEC-04 defines `ItemRevision` and the revision tables | Revisions: introduced by SPEC-04, extended by SPEC-11 |
| Impact walk and verdicts | Introduced by SPEC-12 | SPEC-04 builds a one-round walk with `unaffected` verdicts and the `walk_rounds` and `verdicts` tables | Introduced by SPEC-04 (one round), extended by SPEC-12 and SPEC-16 |
| Lanes and station registry | Introduced by SPEC-02 | SPEC-02 creates lanes; SPEC-06 owns `[stations.<id>]`, slots and sessions | Lanes: SPEC-02; station registry: SPEC-06 |
| Kernel SDK | Introduced by SPEC-03, extended by SPEC-13, SPEC-17, SPEC-19 | SPEC-06 and SPEC-08 define the 0.1.0 port contracts | Add SPEC-06 and SPEC-08 as contributors to 0.1.0 |

**X4. The run manifest lacks the configuration hashes.** See SPEC-01 review 2, N5. SPEC-06's REQ-0605 should then list the two hashes, and AC-0605-1 should assert them.

**X5. Kernel error codes have no registration path below `platform`.** SPEC-01 says later specifications register codes "through SPEC-03's registry". `store` (SPEC-02) cannot import `platform`, yet it registers `storage_limit` and three more codes.
*Change (SPEC-01, SPEC-03):* kernel codes are declared in `grindstone.contracts.errors`, one closed list per class that each kernel specification appends to. The registry is only for factory codes. The `core` registration in SPEC-03 copies the kernel list.

**X6. Specification-level dependency cycles (checklist item 6).**
- **SPEC-06 and SPEC-08.** Each depends on the other. See the judgment on question 3 below.
- **SPEC-05 and SPEC-10.** SPEC-05's `make secrets` uses "the parameters SPEC-10 sets", and SPEC-10 depends on SPEC-05. *Change:* SPEC-05 owns the Argon2id parameters (it writes the hash), and SPEC-10 reads them.
- **SPEC-06 and SPEC-07.** SPEC-07 depends on SPEC-06. SPEC-06 uses SPEC-07's token minting only through a function the composition root registers, which is a correct inversion. *Change:* SPEC-06 should say that it defines the hook and does not depend on SPEC-07.

**X7. Foundation text to align at the next revision (operator; editorial unless noted).**
- The Concepts tab's blob store paragraph still names `budget_exhausted`. ADR-37 removed it; SPEC-02 already uses `storage_limit`.
- The Components tab's configuration table still lists "budgets" for projects (ADR-37: read "limits").
- The Components tab names only `delegate` and `ask(need="operator")` as suspending tools. SPEC-06 and SPEC-07 make `request_permission` suspend too. That applies the Concepts tab's rule that "no task ever holds a lane while it waits", but the Interfaces text should say so.
- Concepts, "Identity: `PREFIX-n`", against kinds that declare a pattern (SPEC-01 review 2, N6).
- The task lifecycle's "any delivery completed": state that a delivery is complete when the port reaches `delivered` (judgment 2c below).
- ADR-26's port operations need a new record, not an editorial change: see the architecture review, A2.

**X8. Kernel neutrality (checklist item 19), minor.** Kernel specifications should rephrase these in kernel terms, or move them to SPEC-09:
- SPEC-02 names "the GitHub adapter";
- SPEC-04 names the SDLC states `implemented` and `verified` in its scope;
- SPEC-06 sets `MCP_TOOL_TIMEOUT`, a Claude Code variable, from `work` (also against ADR-41's rule that no Claude-specific path enters the kernel);
- SPEC-08 speaks of pull requests in its risk and observe text.

FF-12 arrives at M2. These are the lines it would flag first.

## The author's questions

**1. Do any new dependencies need a decision record?**

Playbook rule 6 lists "adds … a dependency" among the choices that need a record, but its first sentence leaves choices "inside one module or one factory" to the specification. Review 1 accepted SPEC-01's dependencies as specification decisions under checklist item 13. The reviewer reads rule 6 as covering a dependency that crosses a module or factory boundary, or one that contradicts a record.

| Dependency | Judgment |
| --- | --- |
| SQLAlchemy 2.1.5, direct (SPEC-02) | No record. Used only inside `store`, behind the unit of work; already in the lockfile through DBOS. DEC-0201 suffices. |
| PyYAML 6.0.3 (SPEC-03; SPEC-04 also parses bundles) | No record. The foundation fixes YAML for manifests. One safe-load helper in `platform`, which `intent` may use, keeps it to one call site. |
| packaging 26.3 (SPEC-03) | No record. Inside `platform`, and already locked. |
| argon2-cffi 25.1.0 (SPEC-10) | No record. Inside `surface` and the secrets script. |
| PyJWT 2.15.1 with cryptography 50.0.2 (SPEC-09) | No record: inside one factory. But SPEC-09 must add a DEC stating the reason and the rejected options (rule 9, checklist item 13), which it does not yet do. |
| Playwright 1.64.1 (SPEC-10) | No record: a test dependency, with its reason in DEC-1004. |
| TypeScript 6.0.3 in `web/` (SPEC-10) | **Needs a record.** ADR-01 commits to "the latest stable release" of every dependency, and 7.0.2 is the latest. Pinning 6.0.3 is right on the facts, because the SvelteKit 3.1.0 and svelte-check 4.7.7 peer ranges stop at TypeScript 6 (checked on npm), but it contradicts a record's text. Proposed record: amend ADR-01 so that a dependency is the latest stable release compatible with the other pins; each exception names its constraint in `docs/m0/versions.md` and is re-checked at every upgrade. |

Every pin in `docs/m0/versions.md` under "Resolved for the M1 specifications" matched the registries on 17 October 2026, release dates included. So did `pytest` 9.1.1 and `dbos` 3.3.0.

The reviewer also recommends that the operator reword rule 6 at the next foundation revision, so that later reviews do not re-litigate this: "a dependency that crosses a module or factory boundary, is exposed through a contract or the SDK, or contradicts a record".

**2. M1 thinnings of foundation text that is not an ADR.** All three are acceptable without a record, under the conditions stated. Each narrows a mechanism for M1 without changing what an existing name means, and each names the specification that restores the full behaviour.

- **(a) A factory is enabled by the operator's configuration command, not a `scope` decision (SPEC-03, OQ-0301).** The protection the `scope` decision gives, that a person approves new vocabulary, specialists and grants, still holds: only the authenticated operator can run the command, and it is recorded with provenance. Conditions:
  - OQ-0301 also names the grants (tiers, secrets), which the Factories tab likewise puts on that decision;
  - the configuration version's provenance records `author_kind: person`;
  - no agent-facing or policy path can write project configuration (already REQ-0311);
  - SPEC-15 converts enabling into the decision, as OQ-0301 says.
- **(b) Approval verdicts are `unaffected` only (SPEC-04, DEC-0402).** One round is then a fixed point by construction, so I-13 holds. An affected item is handled by rejecting and redrafting a larger ChangeSet, which is an `amend` done by hand. The answer schema grows additively when SPEC-16 adds the other verdicts. Conditions:
  - the approval card says, beside the verdict inputs, that "affected" means reject and redraft;
  - SPEC-04 fixes its moved-base defect (SPEC-04 review, F1), which is independent of this thinning.
- **(c) A task is done once its delivery is `delivered`, before merge (SPEC-08, DEC-0805).** This matches S1: the `delivery` decision approves delivery, the pull request opens with its status, and the merge is observed afterwards, while REQ-0101 waits for `verified`. It also matches ADR-40, where only unenforced mode has Grindstone merge. DEC-0805's reasoning is permanent, not M1-only, so record it as the meaning of "any delivery completed" in the task lifecycle (X7). Conditions:
  - a delivery observed `closed` without merge after its task is `done` raises an escalation, so delivered-but-abandoned work is visible (today nothing happens);
  - SPEC-08 states the M1 path for a delivered task whose evidence goes stale: the status goes `pending`, nothing re-checks until SPEC-12, and the operator's way out is a new `/implement` run.

**3. SPEC-06 and SPEC-08 are acyclic only per module.** Checklist item 6 asks for no cycles between specifications, and SPEC-06 depends on SPEC-08 while SPEC-08 depends on SPEC-06. The per-module argument (`stations` ← `evidence` ← `work`) is correct as far as it goes, but X1 shows it is incomplete: `work` → `delivery` also breaks the map.

*Judgment:* split SPEC-06 into two numbered parts under the same ID, as the playbook allows: part 1 for `stations` and the agent host core, part 2 for `work`. The specification-level graph is then part 1 ← SPEC-08 ← part 2, a DAG. This costs a restructure, not a redesign. It also brings SPEC-06, at about twice the playbook's four pages, back toward one sitting (checklist item 18). Accepting per-module acyclicity instead would be a change to the playbook, which only the operator can make.

**4. SPEC-05's root entrypoints copy 0600 secrets into each service user's tmpfs (DEC-0501).** *Sound.* The alternatives it rejects are worse:
- world-readable mounts let every agent user in `agent-host` read the host keys;
- environment variables leak into agents through `@ahpd/agent-acp`'s environment merge, as SPK-1 found;
- owner changes on the host make install host-specific.

The entrypoint holds only `DAC_READ_SEARCH` (with `SETUID`, `SETGID`, and `CHOWN` on the host) for a few lines, then hands over with an empty bounding set. AC-0504-1 checks the final capability sets on the real images, and REQ-0514 fails closed on a world-readable source. Conditions, all minor (SPEC-05 review):
- reconcile the `postgres` row with the blanket `cap_drop: ALL`;
- cite a primary source for Compose ignoring per-secret `uid`, `gid` and `mode` outside Swarm;
- say which tool computes Argon2id inside `make secrets` on the host.

## Proposed records

Neither has a number yet. The operator assigns numbers on acceptance, and FF-13 refuses a number cited before it exists.
1. **Delivery port operations** (amends ADR-26). The port has the operations SPEC-08 needs, with neutral names and no-op defaults for adapters whose remote has no gate. See the architecture review, A2.
2. **Dependency currency** (amends ADR-01). The latest stable release compatible with the other pins, with exceptions recorded and re-checked (question 1 above).

## Next

1. The author revises SPEC-01 to SPEC-10 from these files. Blocking findings first; X1 and X2 touch several specifications at once.
2. The operator:
   - decides the two proposed records;
   - amends the ownership table (X3);
   - schedules the editorial foundation alignments (X7);
   - decides whether rule 6 is reworded.
3. A short confirmation pass checks the blocking findings closed. The minor ones can be checked by the author's own checklist run. Then the operator approves the ten.
