# SPEC-04 review 1

Reviewer: a session that wrote none of SPEC-01 to SPEC-10 (17 October 2026). Checked against the validation checklist and the foundation v4.5. Cross-cutting findings are in `M1-specifications-review-1.md`.

**Verdict: changes required.** One blocking finding (F1), plus X2 (FF-08 must be built here) and the ownership-table rows in X3. The rest is a careful thin slice:
- only apply writes revisions (I-01, I-02);
- edges come from typed references;
- decisions carry recommendations and context hashes;
- continuations start exactly once from the answer's event.

The `unaffected`-only thinning is acceptable (summary, question 2b).

## Blocking

**F1. A moved base can apply a stale revision on its old approval, a lost update.** REQ-0415 and design step 3: when a base hash no longer matches at apply, the ChangeSet is re-walked, and "applies on the existing approval if the reached set is unchanged". The base moves only when an item in the set was revised by another applied ChangeSet. The stored proposal carries the item's full fields, drafted against the old base, so applying it silently reverts the other change. The operator never sees the diff that actually applies, against the new base. That contradicts M3-03's "nothing lost", which SPEC-04's AC-0414-2 and AC-0415-1 are the first form of, and the reason the foundation has a base-revision check at all.
*Change:* in M1, a moved base on any proposed item supersedes the approval. A new approval is raised with the diffs recomputed against the new base, or the ChangeSet is refused and redrafted. Re-walking alone is not enough. The foundation's rule, "approval is asked again only if the review set changed", then holds if the review set is read to include the proposed revisions' diffs. Say so, and leave field-level merging to SPEC-16. Rewrite AC-0415-1: a ChangeSet whose base moved is never applied without an approval whose context hash covers the new base.

## Minor

**F2. Lifecycle states rewritten at start-up versus states still in use.** `intent.lifecycle_states` is rewritten from the registries at each start, and `items` references it. A factory upgrade that removes a state items still hold makes the rewrite violate the reference. *Change:* say that start-up refuses such a factory version (`manifest_invalid`, naming the state and the count of items), which pauses its projects (SPEC-03, REQ-0304). Upgrade steps that map states are SPEC-13's.

**F3. ID allocation and imported numbers.** `id_counters` never reuses a number it allocated, but a kind can also take imported IDs: an operator importing `FND-7` before the counter reaches 7. *Change:* allocation skips numbers already taken in the project (REQ-0407), and AC-0407-1 covers an import followed by allocation.

**F4. The type of `core.interface.contract`.** It is `text` in its first form. The Factories tab makes it structured content "validated against the shape's JSON Schema". Changing a `core` field's type later is not additive, and kernel kinds are what every factory relies on (I-18). *Change:* either declare it now as the JSON-in-text form SPEC-11 will validate, saying so, or add the structured field in SPEC-11 under a new name. Record the choice in OQ form.

**F5. Lifecycle constraints.** DEC-0405 uses a reference table where the Components tab says "every lifecycle column has a database enum". The meaning, that the database refuses an undeclared state, holds. No change is needed in SPEC-04. The operator may want the Components wording to say "an enum or an equivalent constraint" (summary, X7).

**F6. Neutral wording (summary, X8).** The out-of-scope line naming SDLC states (`implemented`, `verified`) becomes "writers other than `changeset` for factory lifecycles".

**F7. A note for SPEC-15.** The seed classes (`approval` and `escalation` at `l2`) are fine. Nothing answers by policy before SPEC-25.

## Checklist

| # | Item | Result |
| --- | --- | --- |
| 1 | Sections present | pass |
| 2 | Requirements testable | pass |
| 3 | AC per requirement | pass |
| 4 | Exit criteria mapped | pass (M1-01, intake clause) |
| 5 | Citations, no contradiction | **fail**: F1 (ChangeSet "Approval and apply"; M3-03's intent) |
| 6 | Dependencies | pass (SPEC-01 to SPEC-03) |
| 7 | Ownership | pass in the specification; table rows for revisions and the walk (X3) |
| 8 | Idempotency | pass (client keys on drafts and answers; AC-0418-1) |
| 9 | Typed boundaries | pass |
| 10 | Migration | pass; F2 for factory upgrades |
| 11 | Trust boundaries | pass (intake `untrusted`; flags kernel-set only) |
| 12 | Derivations computed | pass |
| 13 | Dependencies | pass (none new; PyYAML through SPEC-03) |
| 14 | Cross-module choices as records | pass |
| 15 | Typed errors | pass |
| 16 | Test plan | pass |
| 17 | Terms | pass |
| 18 | One sitting | pass |
| 19 | Kernel names no factory name | minor: F6 |
| 20 | Factory 5F | n/a |
| 21 | Maker and prover | pass (ChangeSets approved by a person) |
| 22 | Cooperation | n/a |
| 23 | Irreversible actions | n/a (everything here is revertible by a later ChangeSet) |
| 24 | Fitness functions | **fail**: X2 (FF-08 is "extended" but built nowhere) |
