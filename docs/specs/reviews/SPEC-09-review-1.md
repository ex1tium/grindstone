# SPEC-09 review 1

Reviewer: a session that wrote none of SPEC-01 to SPEC-10 (17 October 2026). Checked against the validation checklist (factory items 20 to 23 included), the foundation's Factories tab, ADR-27, ADR-40, SPK-4, and the SDK 0.1.0 surface SPEC-03, SPEC-06 and SPEC-08 define. Cross-cutting findings are in `M1-specifications-review-1.md`.

**Verdict: changes required.** Two blocking findings (F1, F2). The factory is a convincing first user of the seam:
- data first, with code only for the adapter, the provider, the resolver and the method;
- git hygiene that never runs repository configuration;
- copy-back that never runs git in the agent's workspace (DEC-0901, the right call);
- annotations read from the verified commit, not from the test run;
- an adapter built on SPK-4's measured calls.

## Blocking

**F1. Collect can write outside the private worktree through a symlink in the base.** Collect walks the workspace without following symlinks (good), then "writes [each changed file] into a private worktree `work/<run>` checked out at `base`". Base content is untrusted (B3). Suppose the base commit contains a symlink `docs -> ../../..`. The agent deletes it in its workspace and creates a real directory `docs/` with a file `docs/x`. Collect finds `docs/x` as a changed regular file and writes it into the worktree, where `docs` is still the base's symlink. The write follows the symlink and lands outside the worktree, on the control plane's `repos` volume: another project's mirror, or the factory's own storage. QS-06 and I-09 forbid exactly this kind of repository-borne effect in the control plane.
*Change:* build the commit without writing the tree through the filesystem. For each changed path, `git hash-object -w --stdin` the bytes (or record a symlink's target as data), apply additions, deletions and type changes to an index with `git update-index --index-info` from `base`'s tree, then run `write-tree` and `commit-tree`. No path is ever opened in a checkout. If a worktree is kept, every write must use `openat` with `O_NOFOLLOW` at every component, and a type change (symlink to directory) must be processed as delete-then-add. Add a security criterion with exactly this fixture.

**F2. The test reviewer cannot see the base, so it cannot judge "weakened or deleted".** QS-01 and M1-07 rest on the test reviewer failing a weakened test. Its prompt asks it to judge tests "not weakened or deleted against the base". Its workspace, though, is materialized from the subject alone, by `git archive <sha>` with no `.git` (REQ-0914, SPEC-06 DEC-0604), and its inputs pin only items. Nothing gives it the base or the diff. A deleted test simply is not there to see.
*Change:* collect produces a diff of the commit against its base as a declared output blob (paths, statuses, the unified diff, bounded in size). The review check's `params` carry it, and the reviewer's prompt includes it. Alternatively, the resolver materializes both base and subject. Extend AC-0907-1 so the scripted reviewer's failure cites the deleted assertion it saw in the diff.

## Minor

**F3. The ticket lifecycle drops `proposed`.** The Factories tab gives `proposed → ready → …`, and SPEC-09 starts tickets at `ready` without saying why. (For requirements it explains that `draft` is an unapproved revision.) *Change:* give the reason. A ticket is proposed only while it is a revision in an unapproved ChangeDraft, as with requirements. Note that `/plan`'s breakdown (SPEC-20) may need `proposed` for approved but not yet scheduled tickets.

**F4. Criteria whose method M1 cannot check.** REQ-0905 adds the CI suite for criteria with method `test` and a review for every criterion. A criterion with method `command` or `manual` therefore gets only a review, a weaker proof than it names. *Change:* `/implement` refuses, at task creation, a ticket with a criterion whose method M1 cannot run (`manual` until SPEC-15; `command` unless the CI suite also maps it), naming the criterion. Alternatively, map `command` to a named gate.

**F5. The PyJWT and cryptography choice needs a DEC.** The dependencies are listed with their versions (both the latest on PyPI, checked) but without a reason or rejected options (checklist item 13, rule 9). *Change:* add a DEC. The reason: RS256 needs an RSA implementation, so `cryptography` is unavoidable, and PyJWT is a small, standard wrapper over it. Rejected: hand-built JWTs over `cryptography` (custom code for a solved problem), and a GitHub client library (a large dependency for six calls). No record is needed (summary, question 1).

**F6. Contracts the factory uses must be SDK exports.** `ReviewVerdict`, `CollectOutcome`, `ModeObservation`, `VerificationState` and the job payload are used here and must be exported by `grindstone.sdk` (architecture review, A4).

**F7. The meaning of "against the ticket's current item hashes" (M1-02).** Evidence inputs are each criterion plus its one-hop check dependencies, which is the requirement. The ticket's own hash is not among them, because `sdlc.implements` is not a check dependency. A semantic edit to the ticket's goal therefore leaves the status `success`. *Change:* state this reading of M1-02, that the ticket's items are its requirements and criteria. Or mark `sdlc.implements` as a check dependency so a ticket edit also returns the status to pending. The reviewer prefers stating the reading: tickets change scope, not what a criterion means.

**F8. Bypass coverage.** As SPEC-08 review F2: published-path changes are seen only while a delivery is open. Say so in REQ-0919.

## Checklist

| # | Item | Result |
| --- | --- | --- |
| 1 | Sections present (5F included) | pass |
| 2 | Requirements testable | pass |
| 3 | AC per requirement | pass |
| 4 | Exit criteria mapped | pass (M1-01, M1-02, M1-05, M1-07, M1-08 clauses as the spec map assigns) |
| 5 | Citations, no contradiction | **fail**: F2 (QS-01, M1-07 cannot be met as designed) |
| 6 | Dependencies | pass (SDK 0.1.0 only; port contracts from SPEC-06 and SPEC-08) |
| 7 | Ownership | pass (factory rows of the ownership table) |
| 8 | Idempotency and crash tests | pass (collect by run and branch; deliver by head-branch lookup; status by lookup) |
| 9 | Typed boundaries | pass (every GitHub response parsed by a bounded contract) |
| 10 | Migration | pass |
| 11 | Trust boundaries | **fail**: F1 |
| 12 | Derivations computed | pass |
| 13 | Dependencies pinned from a primary source | minor: F5. Versions verified: `pyjwt` 2.15.1, `cryptography` 50.0.2, `pytest` 9.1.1 are the latest on PyPI |
| 14 | Cross-module choices as records | pass |
| 15 | Typed errors | pass |
| 16 | Test plan | pass (fake GitHub for mechanisms; live runs for M1-01, M1-02, M1-08) |
| 17 | Terms | pass |
| 18 | One sitting | pass |
| 19 | Kernel names no factory name | n/a: factory specification |
| 20 | Namespace, SDK only, complete 5F | pass. The conformance kit arrives with SPEC-13; the loader rules stand in, as stated |
| 21 | Maker and prover | pass in structure (the implementer makes; the CI suite and the test reviewer prove, on a different model slot); F2 is what makes the reviewer's proof meaningful |
| 22 | Cooperation | n/a |
| 23 | Irreversible actions | pass, as SPEC-08 |
| 24 | Fitness functions | pass (FF-01 for factory imports, FF-10 for the adapter's and provider's effects) |
