# SPK-4 — GitHub mechanics

Status: planned · Box: 1 day · Settles: Q-7; how the verification status gates merge (M1-02, ADR-27); how the delivery mode is detected and how Grindstone merges safely in unenforced mode (ADR-40)

## Why

The verification status is the one signal that lets a pull request merge (I-08). It must be impossible to satisfy from anywhere but the Grindstone App, and it must stop counting the moment the head changes.

## Setup

`ex1tium/grindstone-testbed`, **public** so its ruleset is enforced on the free plan, with the GitHub App installed (`docs/m0/operator-setup.md`, steps 2 and 3). A short script holding the App key mints installation tokens and calls the REST API.

## Experiments

1. **App status satisfies the required check.** Open a pull request; the App sets `grindstone/verification` to success on the head. *Pass:* merge is allowed.
2. **Forged status from inside the repository.** A GitHub Actions workflow in the testbed sets a status with the same context, using its own token. *Pass:* the ruleset still blocks merge, because the required check's source is the App. This is the property that keeps repository code from setting its own verdict (QS-03).
3. **Stale head.** Push a new commit after success. *Pass:* the old status does not count; merge is blocked until a status is set on the new head.
4. **Behind the base, with strict checks** (Q-7). Advance the base branch. *Pass:* merge is blocked until the branch is updated and a new status is set at the new head.
5. **Auto-merge** (Q-7). Arm auto-merge on a pull request that is behind. *Pass:* it waits for the update and for the status at the new head, then merges; disarming works. Auto-merge is used only at L3 (R2); this only records the behaviour.
6. **Lookup by branch.** Find pull requests by head branch, including closed and merged ones. *Pass:* an idempotent "find or create" for delivery is possible: delivery is idempotent by `(project, ticket, subject commit)` (Factories tab, "Delivery").
7. **Polling budget.** Measure the REST calls one poll of pull-request state, review comments and failing checks costs (ADR-32), against the installation rate limit. Record conditional requests (`ETag`) support.
8. **Push without hooks.** From a bare mirror and a private clone, push a commit made with hooks disabled, using the installation token. *Pass:* the push works, and no hook from the repository runs (QS-06).

9. **Detecting the delivery mode** (ADR-40). Find the API call that tells whether the target branch's rules actually require `grindstone/verification` from the App: the rules in force on a branch, compared with the rulesets that exist. Run it on the public testbed (enforced), then switch the testbed to private for the length of this experiment (unenforced on the free plan) and run it again; switch it back to public afterwards. *Pass:* the call distinguishes the two cases with no false "enforced"; record the exact responses.
10. **Merging with the verified head** (ADR-40). In unenforced mode Grindstone merges itself. Merge through the API passing the head SHA that was verified; push a commit between verification and merge. *Pass:* the merge is refused, and nothing reaches the default branch.
11. **Detecting a bypass** (ADR-40). On the private testbed, merge a pull request in the GitHub UI and push a change directly to the default branch. *Pass:* both are visible to a poll (the merge's actor and method, and the commits on the branch that no delivery produced), which is what `observe` needs to raise `delivery_bypass`.

## Record

API endpoints and headers used; ruleset JSON exported; rate-limit numbers; the exact status context name and description length limits.

## Fallback

If experiment 2 fails, a forged status could merge a pull request in enforced mode: stop and raise a decision record before the M1 specifications. If experiment 9 cannot distinguish the modes, treat every target as unenforced: Grindstone always merges itself and always watches for bypasses. If the commit-status API cannot be source-restricted, use a check run created by the App, which is attributed to the App by GitHub.
