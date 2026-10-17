# SPK-4 — GitHub mechanics

Status: planned · Box: 1 day · Settles: Q-7; how the verification status gates merge (M1-02, ADR-27)

## Why

The verification status is the one signal that lets a pull request merge (I-08). It must be impossible to satisfy from anywhere but the Grindstone App, and it must stop counting the moment the head changes.

## Setup

`ex1tium/grindstone-testbed` with its ruleset and the GitHub App installed (`docs/m0/operator-setup.md`, steps 2 and 3). A short script holding the App key mints installation tokens and calls the REST API.

## Experiments

1. **App status satisfies the required check.** Open a pull request; the App sets `grindstone/verification` to success on the head. *Pass:* merge is allowed.
2. **Forged status from inside the repository.** A GitHub Actions workflow in the testbed sets a status with the same context, using its own token. *Pass:* the ruleset still blocks merge, because the required check's source is the App. This is the property that keeps repository code from setting its own verdict (QS-03).
3. **Stale head.** Push a new commit after success. *Pass:* the old status does not count; merge is blocked until a status is set on the new head.
4. **Behind the base, with strict checks** (Q-7). Advance the base branch. *Pass:* merge is blocked until the branch is updated and a new status is set at the new head.
5. **Auto-merge** (Q-7). Arm auto-merge on a pull request that is behind. *Pass:* it waits for the update and for the status at the new head, then merges; disarming works. Auto-merge is used only at L3 (R2); this only records the behaviour.
6. **Lookup by branch.** Find pull requests by head branch, including closed and merged ones. *Pass:* an idempotent "find or create" for delivery is possible: delivery is idempotent by `(project, ticket, subject commit)` (Factories tab, "Delivery").
7. **Polling budget.** Measure the REST calls one poll of pull-request state, review comments and failing checks costs (ADR-32), against the installation rate limit. Record conditional requests (`ETag`) support.
8. **Push without hooks.** From a bare mirror and a private clone, push a commit made with hooks disabled, using the installation token. *Pass:* the push works, and no hook from the repository runs (QS-06).

## Record

API endpoints and headers used; ruleset JSON exported; rate-limit numbers; the exact status context name and description length limits.

## Fallback

If experiment 2 fails, a forged status could merge a pull request: stop and raise a decision record before M1 specifications. If the commit-status API cannot be source-restricted, use a check run created by the App, which is attributed to the App by GitHub.
