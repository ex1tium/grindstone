# SPK-4 — GitHub mechanics

Status: in progress (blocked: App calls cannot run in a cloud session) · Box: 1 day · Settles: Q-7; how the verification status gates merge (M1-02, ADR-27); how the delivery mode is detected and how Grindstone merges safely in unenforced mode (ADR-40)

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

## Report (partial, 17 October 2026)

Run from a Claude Code cloud session. Spike code: `spk4/` on branch `claude/youthful-franklin-oq4j5j` of `ex1tium/grindstone-testbed` (never merged); spike pull request ex1tium/grindstone-testbed#1, closed.

### Blocker: the cloud session cannot act as the App

The session's outbound proxy mediates `api.github.com`:

- It **replaces the `Authorization` header** with its own credentials: `GET /user` answers `ex1tium` whatever token is sent, including a bogus one or none. Any call from a session therefore acts as the operator's account, not as the App.
- It **refuses** `/app/*` (so no installation token can be minted), `/installation/*`, `/apps/*`, writes to `/repos/{repo}/statuses/{sha}`, and the Actions API (workflow dispatch, `actions/permissions`): `403 "... not permitted through this proxy"`.

So no status can be set from a session under any identity, and experiments 1 to 5, 10 and 11 cannot run here. Routing around the proxy is not an option. They need a host that reaches `api.github.com` directly: the operator's machine or the stable self-hosting instance. `gh.py` already mints the JWT and the installation token for that run. This also means a cloud session can never hold the App identity in M1: delivery must run where the App key lives (I-08).

### Environment check (Next step 1)

- The four `GRINDSTONE_*` variables are set; the key decodes to a 2048-bit RSA key and signs a JWT. The token exchange could not be tried (blocked above).
- `GET /repos/ex1tium/grindstone-testbed/rules/branches/main` (the rules in force on `main`): deletion, non-fast-forward, pull request (0 approvals, all three merge methods) and `required_status_checks` with `strict_required_status_checks_policy: true` and `{"context": "grindstone/verification", "integration_id": 5358336}`. The `integration_id` equals `GRINDSTONE_GITHUB_APP_ID` (compared, not printed), so **the check's source is already restricted to the App**; no first status was needed.
- Drift from `.github/rulesets/testbed-main.json`: the live ruleset adds `require_extra_approval_for_unattributed_changes: true` (a field GitHub fills in on import) and the `integration_id` the operator set afterwards. `bypass_actors` is empty; `current_user_can_bypass: never`.

### Experiment 2 (forged status): not run

Actions are not registered on the testbed (`GET /actions/workflows` lists none although `.github/workflows/forge-status.yml` is on `main`, and `/actions/runs` is empty): **check Settings → Actions is enabled**. Dispatch is refused through the proxy, and so is a status posted by the operator's account. Baseline only: with no status, the open pull request reads `mergeable: true`, `mergeable_state: "blocked"`.

### Experiment 6 (lookup by branch): pass

`GET /repos/{repo}/pulls?head={owner}:{branch}&state=all` finds the pull request by head branch whether open or closed (`state=open` returns it before closing, `state=closed` after; a missing branch returns `[]`). `GET /repos/{repo}/commits/{sha}/pulls` maps a commit to its pull requests. A merged pull request has not been looked up yet (no merge is possible without the App status); `merged_at` distinguishes it from a closed one.

### Experiment 7 (polling budget): partly measured

One poll of one pull request is 6 REST calls: `pulls/{n}` (state, head SHA, `mergeable_state`), `pulls/{n}/comments`, `pulls/{n}/reviews`, `issues/{n}/comments`, `commits/{sha}/status`, `commits/{sha}/check-runs`. Every one returns an `ETag`, and repeating it with `If-None-Match` returns `304` with no change in `core.used`: an unchanged pull request costs nothing against the limit. Not yet measured: the installation's own limit (the proxy reports its identity's, 15 000 an hour; the proxy also hides the `X-RateLimit-*` headers), and whether the proxy caches.

### Experiment 9 (delivery mode), public half

On the public testbed, `GET /repos/{repo}/rules/branches/main` returns the `required_status_checks` rule with the App's `integration_id`, and `GET /repos/{repo}/rulesets` returns the ruleset with `enforcement: "active"`. Detection rule to test on the private half: enforced only if the rules-in-force call lists `grindstone/verification` with Grindstone's `integration_id` and `strict` true. Switching the testbed private needs an admin write, which the proxy does not allow either.

### Remaining

Experiments 1 to 5 and 8 to 11, from a host with direct access to `api.github.com`, after Actions are enabled on the testbed.
