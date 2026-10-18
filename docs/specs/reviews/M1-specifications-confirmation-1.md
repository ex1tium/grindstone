# M1 specifications, confirmation 1: the blocking findings of review 1

Reviewer: a session that wrote none of SPEC-01 to SPEC-10, none of their reviews and none of revision 1 (18 October 2026). This is the confirmation pass that `M1-specifications-revision-1.md` asks for. It checks the blocking findings that file lists at its end:
- X1 and X2;
- SPEC-02 F1 and SPEC-04 F1;
- SPEC-06 F1 to F3, with the different fix for F1;
- SPEC-08 F1;
- SPEC-09 F1 and F2;
- A1 to A3 of the SPEC-03 architecture review.

It also judges the three fixes that `docs/m0/status.md` says differ from the reviewer's proposals. The minor findings are left to the author's checklist run, as the revision file says.

Everything was checked against the revised specifications in `docs/specs/`, foundation v4.6 (ADR-45 and the ownership table included), and the module map in `scripts/ff/module_map.py`, which revision 1 did not change. The specifications are not revised here.

## Verdict

**Every blocking finding is closed.** Each one has a requirement, a design paragraph and an acceptance criterion that would fail if the defect came back. The three different fixes are sound, and two of them are better than what the reviewer proposed.

Confirming them turned up four items the author should handle before the operator approves:
- **C1 and C2** are leftovers of two closed findings. Each needs one or two sentences.
- **C3 and C4** are new defects in the mechanisms that SPEC-08 F1 and SPEC-09 F1 fixed. Each needs a short design change and one acceptance criterion.

**Recommendation:** approve after C1 to C4. A re-check of those four alone is enough. The rest of this pass does not need repeating.

## The blocking findings

| Finding | Where it is closed | Result |
| --- | --- | --- |
| **X1**, `work` → `change.draft` | SPEC-04 REQ-0421, DEC-0406, AC-0421-1. SPEC-06 part 2 REQ-0615, collect step 3, AC-0615-1. | Closed. `work` emits `change.draft_requested` and never calls `change`. |
| **X1**, `work` → `delivery.prepare` | SPEC-06 part 2 "Delivery hand-over" and its dependency note. SPEC-08 "Delivering" step 1. | Closed. `delivery` prepares from its consumer of `task.transitioned`, whose payload carries the target and subject. `work` learns of the outcome from `delivery.delivered` and `delivery.failed` events. |
| **X1**, `delivery` → `change.draft` | SPEC-08 REQ-0816, "Observe", AC-0816-1. | Closed. Bypass emits the same draft request with trust `untrusted`. |
| **X1**, `evidence` reads the task's subject | SPEC-08 "Plans" step 1, "Freshness", `evidence.task_subjects`. | Closed. `freshness` reads only `evidence`, `intent` and `stations`, all on `evidence`'s list. |
| **X2**, FF-07 and FF-09 | SPEC-02 REQ-0215 and REQ-0216, TKT-0206, AC-0215-1 and AC-0216-1, with fixtures. The DBOS outputs table is exempt (F5). | Closed. |
| **X2**, FF-08 | SPEC-04 REQ-0420, TKT-0405, AC-0420-1, `scripts/ff/single_writer.py`. SPEC-06 parts 1 and 2 and SPEC-08 register their own columns. | Closed. |
| **SPEC-02 F1**, keys under `fork` | REQ-0204: the key is `<causing record ID>:<step name>[:<n>]`, carried as a workflow input, and never contains the DBOS workflow ID. AC-0204-3 kills a step after its effect, forks the workflow and expects one effect. | Closed. The owners' keys follow the same rule: `<run>:s<k>` (SPEC-06), `<delivery>:deliver` (SPEC-08), and the delivery consumer keyed by its event. |
| **SPEC-04 F1**, lost update on a moved base | REQ-0415, "Approval and apply" step 3, the `awaiting_approval → walked` transition, AC-0415-1. | Closed: a moved base never applies on its old approval, and the new card shows the diff against the new base, including the reversal. One statement is missing (C1). |
| **SPEC-06 F1**, a run's turns as another user | Part 1 REQ-0623, DEC-0606, AC-0623-1. Part 2 REQ-0607, AC-0607-2. SPEC-05 REQ-0505, DEC-0502. | Closed, with the different fix judged below. AC-0623-1 is the criterion the review asked for: two read-only runs suspend and resume and keep their own users. |
| **SPEC-06 F2**, no suspended state | Part 2 REQ-0627: run `active ⇄ suspended` and turn states `open`, `suspended` and `ended`. SPEC-07 REQ-0702 and its token check, step 2, which requires the run `active`, the token's turn current and that turn `open`. AC-0627-1. | Closed. `work.suspend` moves the turn and the run in one unit of work before the tool returns, so the token dies when the decision is raised. |
| **SPEC-06 F3**, configuration hashes in the manifest | SPEC-01 `RunManifest` (`instance_config_hash`, `project_config_hash`), REQ-0110, AC-0110-1. Part 2 REQ-0605, AC-0605-1. | Closed. |
| **SPEC-08 F1**, status-post key | Key `<delivery>:gate:<head>:<post>`, where `post` is the `gate_posts` row's sequence number. REQ-0814, AC-0814-2 (`success → pending → success` gives three posts and three keys). SPEC-09's adapter still skips a post only when the App's latest status already has that state. | Closed. A related race remains, outside what F1 named (C3). |
| **SPEC-09 F1**, symlink escape at collect | REQ-0912, DEC-0906, collect steps 4 and 5. Blobs come from `hash-object`, the tree from a private index loaded from `base`, then `write-tree` and `commit-tree`. A type change is a delete plus an add. AC-0912-3 uses the review's own fixture and a sentinel file. | Closed for writes: no path of a checkout is opened. The read side of collect has a race of the same class (C4). |
| **SPEC-09 F2**, reviewer blind to the base | SPEC-09 REQ-0923, collect step 6, AC-0923-1. The `CollectOutcome.prover_context` comes from part 1. Part 2 REQ-0628 and AC-0628-1 put it into every check task's pins and prompt. The reviewer prompt uses it. AC-0907-1 requires the reviewer to fail citing the deleted assertion in the diff. | Closed. |
| **A1**, SDK contexts | SPEC-03 "Contexts": a `Context` protocol whose implementation lives in the composition root. It is obtained through `platform.context_for(project, factory)`, so factories never build one and the secret check reads the factory the kernel bound. AC-0315-1 and AC-0624-1 check that no adapter can obtain another factory's context. | Closed for what A1 named: no new SDK import, and no context built by a factory. Where the protocols live still breaks FF-01 (C2). |
| **A2**, the delivery port | ADR-45 (foundation v4.6). SPEC-08's `DeliveryAdapter` row, SPEC-03's export table and SPEC-09's call table use its names: `supports`, and `observe_mode` returning `none` for a remote with no gate. The kernel re-checks the gate before `deliver` and before `accept`. AC-0813-1 covers an adapter that supports neither optional operation. | Closed. |
| **A3**, load order | SPEC-03 REQ-0318, DEC-0307, loader steps 3 to 5. Phase 2 runs over the union to a fixed point. AC-0318-1 runs it with both name orders, and also covers a need whose only offer is refused. | Closed. |

The specification graph is now acyclic. Reading every "Depends on" section gives: SPEC-01 ← SPEC-02 ← SPEC-03 ← SPEC-04; SPEC-05; part 1; SPEC-08; part 2; then SPEC-07, SPEC-09 and SPEC-10. Part 2 states that it defines the token-minting hook and does not depend on SPEC-07.

## The three different fixes

`status.md` counts three. The revision file marks only two as different. It labels the third, the runner's network, "the reviewer's recommendation", which is the option SPEC-05 review F3 preferred. All three were checked.

**1. Drafts through one event contract that SPEC-04 owns (X1).** *Sound, and better than the proposal.*
- The proposal had `change` consume `run.collected` and `delivery.bypass_observed`. That would have made SPEC-04 depend on SPEC-06 and SPEC-08 and created the cycle DEC-0406 names.
- `ChangeDraftRequested` lives in `grindstone.contracts.change`, below every emitter. It carries its proposals as a blob reference and has a client key unique per project, so an event delivered twice drafts once (AC-0421-1).
- The approval for an intake draft is still flagged `untrusted` (I-07).
- One consequence is minor. A refused draft no longer fails the run that asked for it, because the task has already moved to `verifying`. SPEC-04 says the refusal "is recorded on the request … for the emitter's owner to show" but names neither the record nor the place it is shown. The author's checklist run should name both, for example an event SPEC-10 shows on the task.

**2. A run binds one agent user from a pool for its life, and lanes stay queues (SPEC-06 F1).** *Sound, and better than the proposal.*
- Binding a run to a lane slot, as proposed, would have let a run suspended on the operator hold a lane. That breaks ADR-14 and the Concepts rule that "no task ever holds a lane while it waits", which v4.6 now extends to `request_permission`.
- With a pool, the binding happens in `prepare_workspace`, which the run workflow calls off-lane. So a run waiting for a free user holds no lane, and the wait is visible as `agent_user_unavailable`.
- The user is released only after the workspace is discarded, on every path, including retry, host loss and cancellation.
- Nothing in the foundation ties agent users to lane slots. The foundation says only that agents run "under their own Unix user", which still holds.
- If the pool runs out, runs wait but nothing deadlocks: users are freed when runs end or decisions are answered. OQ-0503 and OQ-0604 carry the pool size to the M1 review.
- The fix also makes C4's remedy cheap: one user means one run, so every process of that user can be killed safely.

**3. The runner has no network in M1 (SPEC-05 F3).** *Sound and consistent.*
- DEC-0505 removes `runner-egress`, and AC-0502-1 checks that the `runner` container has only loopback.
- The foundation commits to no runner egress. Its risks table already says "dependencies baked into the toolchain image", and the M0-04 `fixture` job already runs with no network.
- SPEC-08's environment fingerprint includes the image digest, so a rebuilt toolchain image stales the evidence of methods that declare the environment relevant.
- SPEC-09's OQ-0901 was updated for M1-08: Grindstone's own unit tests run in an image the operator builds from the lockfile.
- No check method in SPEC-08 or SPEC-09 installs anything at run time.

## To change before approval

**C1. Where the new bases of a moved-base ChangeSet are recorded (SPEC-04, from F1).** Step 3 recomputes the diffs against the new current revisions, and the new approval's context hash "covers the new bases". Neither the specification nor its tables say where those bases are kept:
- drafts are insert-only, and each proposed revision carries the base it was drafted against;
- apply step 2 re-checks "every base";
- the M1 rules require, again before the approval is raised, "a base equal to the current hash".

Read literally, the re-raised approval is refused by the rules, or the re-check fails on every later answer. Then a ChangeSet whose base moved can never apply.
*Change:* say that the re-walk records the new base per revision (for example on the new walk round, or as a new draft that supersedes the old one). Say that the rules and the apply re-check compare against that recorded base. Extend AC-0415-1 so that answering the new approval applies the ChangeSet.

**C2. Where the port and context protocols live (SPEC-03 A1, SPEC-06 part 1, SPEC-08).** SPEC-03 says "`Context` is a protocol in `grindstone.sdk`", and the SDK "re-exports … the protocols below". Several kernel modules must name these types, and the module map forbids the SDK to all of them:
- `platform`, at loader step 5, checks that every adapter "implements its SDK port", and `platform.context_for` returns a context;
- `stations` calls `WorkspaceProvider` and `SubjectResolver`;
- `evidence` calls `CheckMethod`;
- `delivery` calls `DeliveryAdapter`.

`MODULE_MAP` lists `sdk` for none of them, so typing these calls under pyright strict means an import that FF-01 refuses. This is A1's own subject, building the SDK within FF-01, and the proposal in the architecture review had the same gap.
*Change:* define `Context`, its extensions and the four port protocols in `grindstone.contracts` (for example `grindstone.contracts.ports`), next to the models A4 already places there. `grindstone.sdk` re-exports them, as it does every other name in the export table. TKT-0301 and TKT-0607 name that path.

**C3. Concurrent re-evaluations can leave a stale `success` on the remote (SPEC-08, new, found while confirming F1).**
- Re-evaluation runs in three consumers: `changeset.applied`, `evidence.recorded` and head observations. Under REQ-0319 they run concurrently. Each one computes the state, records a `gate_posts` row when the state differs from the last row for that head, and posts.
- Nothing serializes them per delivery. Take consumer B, started by `evidence.recorded`, which reads the inputs before a ChangeSet changes a criterion and computes `success`. Consumer A, started by that `changeset.applied`, reads after it and computes `pending`.
- If A records and posts first, B then finds its `success` different from the last row (`pending`). B records and posts it, with a new key, as F1's fix intends. The remote ends at `success` for a stale criterion.
- SERIALIZABLE isolation does not prevent this: B can be ordered before the apply and still commit its row and its post last. That breaks M1-02's "succeeds only when … against the current item hashes", in the direction that matters most.

*Change:* serialize re-evaluation per delivery. One option is a DBOS queue per delivery with concurrency 1, or a single workflow per delivery that consumers signal. Another is to take `uow.lock(("verify", delivery))` and recompute under it, and to post only if the row is still the latest for its head when the post step runs. Add a criterion with the interleaving above: the last post must be `pending`.

**C4. Collect can read outside the workspace through a symlink swapped in mid-walk (SPEC-09, new, the read-side twin of F1).**
- Collect walks the workspace without following symlinks, then reads each file "with `O_NOFOLLOW`". `O_NOFOLLOW` guards only the last path component.
- Nothing ends the agent user's processes before collect. Disposing the session ends the agent's child process, and `--pdeathsig` covers only that child. A grandchild started with `setsid` or `nohup` from the agent's shell tool keeps running while the host lives.
- Such a process can replace a directory the walk has already listed with a symlink between the walk and the read. The control plane, reading as its service user, then follows the symlink inside the `grindstone` container, for example into that service's 0600 secret copies under `/run` (SPEC-05).
- The bytes go into the commit and into the diff that SPEC-09 F2's fix hands to the test reviewer, an agent with open egress. That is a path for a control-plane credential to leave through an agent, against I-09, QS-06 and REQ-0503.

*Change:* do both of the following.
- Before `collect`, the host kills every process of the run's bound agent user and confirms none remain. This is safe now that a user belongs to one run (DEC-0606), and SPEC-05's helper can do it as that user.
- Read with directory file descriptors: open each component relative to its parent with `O_NOFOLLOW | O_DIRECTORY`, and the file with `O_NOFOLLOW`, so a swapped component fails the read instead of redirecting it.

Add a security criterion: a background process of the agent user swaps a directory for a symlink to a sentinel file outside the workspace during collect, and the sentinel's content appears neither in the commit nor in the diff.

## Small inconsistencies for the author's checklist run

None of these blocks approval. Each is a line to align:
- SPEC-05 line 104 still says run directories are "under the slot's subtree". They are under the bound agent user's subtree (`agents/<user>/<run>/`).
- `evidence.plan_checks` has two signatures. SPEC-06 part 2 gives `(task, subject, maker, specs + extra_checks)`. SPEC-08 gives `(task, subject, maker, delegators, specs, resolved)`, with `work` resolving prover needs first.
- SPEC-07 calls `work.add_proposals`, which part 2's interface list does not include.
- Part 1's `prepare_workspace(run)` must build a `RunContext` with the task, mode and base, which `stations` cannot read from `work`. Its signature should take them from `work`.
- SPEC-08's "State and ownership" lists `task_subjects` under the `delivery` bullet, though the table is in schema `evidence`.
- SPEC-08's consumer of `task.transitioned` acts on the event's target and subject and cannot read the task's current state. That is right, because the event is the fact. But a task cancelled while `delivering` leaves its `delivery` decision open. Say that `delivery` also consumes `task.transitioned` to `cancelled` and cancels the delivery (REQ-0319).
- SPEC-09's diff is truncated at 1 MiB "with the truncation stated". The reviewer's prompt should say that a truncated diff cannot pass the "not weakened or deleted" judgment without an explicit acknowledgement, so a deletion past the limit is not passed unseen.
- Phase 2 of loading (A3) is order-independent but refuses in one direction only. A factory refused in an early pass because of a capability from a factory refused in the same pass is never reconsidered. That is deterministic and safe. The start-up report should name the other factory's capability, as the risk line in SPEC-03 already promises.

## Next

1. The author makes C1 to C4 and the small alignments above, and runs the checklist.
2. A short re-check of C1 to C4 only, by a session that did not write them.
3. The operator approves the ten specifications (SPEC-06 in two parts). Then the tickets in each section 7 are ready to break down.
