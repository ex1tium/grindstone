# SPK-4 — GitHub mechanics

Status: done · Box: 1 day · Settles: Q-7; how the verification status gates merge (M1-02, ADR-27); how the delivery mode is detected and how Grindstone merges safely in unenforced mode (ADR-40)

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

## Report (17 October 2026)

**Every experiment passed. Q-7 is confirmed and no fallback is needed.**

How it ran: `spk4/run.py` on branch `claude/youthful-franklin-oq4j5j` of `ex1tium/grindstone-testbed` (spike code, never merged), run by the operator on their own machine as the App `grindstone-dev-rootnode` (run `20261017T151254Z`, pull requests ex1tium/grindstone-testbed#2 to ex1tium/grindstone-testbed#9). Raw results: `spk4/results/20261017T151254Z/` on that branch. How to run it: `SPK-4-local-run.md`.

### A cloud session cannot act as the App

A Claude Code cloud session reaches `api.github.com` only through its proxy. The proxy substitutes its own credentials for any `Authorization` header (`GET /user` answers `ex1tium` with a bogus token or none), and it refuses `/app/*`, `/installation/*`, commit-status writes and the Actions API. So every App experiment ran on the operator's machine. The same holds for M1: delivery runs where the App key lives, never in a cloud session (I-08).

### Results

| # | Result | Evidence |
| --- | --- | --- |
| Setup | ok | The installation token was minted from the App key; the installation sees only the testbed. The ruleset's `required_status_checks` entry carries `integration_id` = the App ID, so the source was restricted without a first status. |
| 1 | pass | No status: `blocked`. Pending: `blocked`. App success (creator `grindstone-dev-rootnode[bot]`, type `Bot`): merge with the head SHA accepted (`200`). The run's verdict line says FAIL because the state read `unstable`. That came from the run's own throwaway statuses: optional statuses left pending make `mergeable_state` read `unstable` rather than `clean`. The script now settles them. |
| 2 | pass | Two forgeries of `success` on `grindstone/verification`: one by the operator's own account (an admin, type `User`), one by the repository's own workflow with its `GITHUB_TOKEN` (`github-actions[bot]`, type `Bot`). Either way the pull request stays `blocked`, and the App's merge is refused: `405 Repository rule violations found. Required status check "grindstone/verification" was not set by the expected GitHub app.` (QS-03) |
| 3 | pass | After success, a new commit makes the pull request `blocked`. Merge with the old SHA: `409 Head branch was modified`. Merge with the new SHA and no status: `405 ... Required status check "grindstone/verification" is expected`. A status on the new head makes it `clean`. |
| 4 | pass | After the base advances, the state is `behind` even with a success on the head, and merging is refused (`405`). `PUT /pulls/{n}/update-branch` (as the App) makes a new head, which is `blocked` until it gets its own status; then `clean`, and the merge succeeds. |
| 5 | pass | GraphQL `enablePullRequestAutoMerge` (squash) arms auto-merge as the App, and `disablePullRequestAutoMerge` clears it (`autoMergeRequest: null`). Re-armed: with a success on the behind head it does not merge (`behind`), and it does not update the branch itself. After update-branch, with no status at the new head, it still waits. Once the new head has a status, it merges, merged by `grindstone-dev-rootnode[bot]`. |
| 6 | pass | `GET /repos/{repo}/pulls?head={owner}:{branch}&state=all` finds merged pull requests (#2, #7), closed unmerged ones (#4) and open ones; a branch that never existed returns `[]`. `GET /commits/{sha}/pulls` maps a commit to its pull requests. |
| 7 | recorded | The installation's core limit is 5,000 an hour (the base allowance for an installation on a personal account). One poll of a pull request is 6 calls: `pulls/{n}`, `pulls/{n}/comments`, `pulls/{n}/reviews`, `issues/{n}/comments`, `commits/{sha}/status` and `commits/{sha}/check-runs`. Every one returns an `ETag`, and `If-None-Match` → `304` leaves `x-ratelimit-used` unchanged. So polling an unchanged pull request is free; a changed one costs 6. |
| 8 | pass | Failing hooks planted in the private clone (`pre-commit`, `commit-msg`, `post-commit`, `pre-push`, `reference-transaction`) and in the bare mirror (`pre-receive`, `update`, `post-receive`, `reference-transaction`, `pre-push`). Commit, clone → mirror, mirror → GitHub with the installation token: the push landed with the same SHA, and no hook ran. Hooks are off through `core.hooksPath` pointing at an empty directory, set in the environment (`GIT_CONFIG_COUNT`), which reaches `receive-pack` too. The token reaches git only as an `http.extraHeader` in the environment, never in a URL or argv. |
| 9 | pass | The probe: `GET /repos/{repo}/rules/branches/{branch}` must return `200` with a `required_status_checks` rule, `strict_required_status_checks_policy: true`, and `{"context": "grindstone/verification", "integration_id": <App ID>}`. Public: `200`, enforced. Private (free plan): `/rules/branches/main` and `/rulesets` both answer `403 "Upgrade to GitHub Pro or make this repository public to enable this feature."`, so the probe says unenforced. No false "enforced": any other answer is unenforced. Back to public: enforced again. Raw responses: `e9-*.json`. |
| 10 | pass | Private: verified head H1, then a new push H2. `PUT /pulls/{n}/merge` with `sha` = H1: `409 Head branch was modified`, and `main` did not move. Control: merging H2 with no status at all succeeded (`200`), which confirms nothing else guards an unenforced target. Passing the verified SHA is the only guard. |
| 11 | pass | A merge in the UI: `merged_by` = `ex1tium`, with a two-parent merge commit (merge method). A direct push to `main`: a commit for which `GET /commits/{sha}/pulls` returns no pull request. `GET /repos/{repo}/activity?ref=refs/heads/main` lists each change with its type and actor (`push` by `ex1tium`; `pr_merge` by `ex1tium`; `pr_merge` by `grindstone-dev-rootnode[bot]`), so a delivery's own merges and bypasses are told apart by actor and type. |

### What this settles

- **The verification status gates merge, and only from the App.** On an enforced target, a status from anyone else, whether an admin or the repository's own workflows, does not count, and GitHub names the reason. The required check is pinned by `integration_id` in the ruleset.
- **Q-7, as decided.** With strict checks, a behind branch must be updated and verified again at the new head. Auto-merge waits for both, and it never updates the branch itself. So whoever delivers must call update-branch and then set a fresh status. Disarming works.
- **ADR-40 is buildable as specified.** Mode detection is one call (`rules/branches/{branch}`); a `403`, or a missing App `integration_id`, means unenforced. In unenforced mode, a merge passing the verified SHA is refused after a concurrent push. Bypasses are visible through `merged_by`, commits with no pull request, and the activity API.
- **Delivery's find-or-create** can look pull requests up by head branch across all states.
- **The polling budget**: 6 calls per changed pull request per poll, unchanged ones free with ETags; 5,000 calls an hour per installation.
- **Limits**: a status description is at most 140 characters, and a context at most 255 (one more character is `422`).
- **Pushing without hooks** works from a bare mirror and a private clone with the installation token (QS-06).

### Side findings

- **Workflow registration.** A workflow file that reached the default branch while Actions were off stays unregistered (`GET /actions/workflows` is empty, and dispatch is `404`) even after Actions are enabled and other commits land. It registers only when a push changes the file itself. Pushing that change needs a person or a token with the Workflows permission, which the App does not have.
- The ruleset field `require_extra_approval_for_unattributed_changes: true`, which GitHub added on import, did not block any App merge.
- The runner gained `--merge <PR>`, which sets the App's status and merges, for changes the operator authors on the testbed.
