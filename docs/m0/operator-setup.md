# Operator setup for M0

What only the operator can do, in the order the work needs it. Each step says which exit criterion or spike it unblocks. Development runs in Claude Code cloud sessions (decided after kickoff); the repository's SessionStart hook prepares each session. Secrets never enter this repository or a chat: they live in the cloud environment's settings, in `secrets/` files on a host (ignored by git), or in a password manager.

## 1. Protect `main` on `ex1tium/grindstone` (now)

Settings → Rules → Rulesets → New ruleset → **Import a ruleset**, and choose `.github/rulesets/grindstone-main.json`: pull requests only, squash merge, linear history, no force pushes or deletions, and both CI jobs required on an up-to-date branch. `.github/rulesets/README.md` explains each rule.

Also under Settings → General → Pull Requests: allow squash merging only, and turn on automatically deleting head branches.

**Plan check:** GitHub's free plans enforce rulesets on public repositories only. This repository is public (since 17 October 2026), so the imported ruleset is enforced and Actions minutes are free.

Settings → Code security: turn on Dependabot alerts and security updates, secret scanning and push protection.

## 2. Create the GitHub test repository (M0-04; needed by SPK-4)

Create `ex1tium/grindstone-testbed` and make it **public**: the free plan enforces rulesets only on public repositories, and the testbed only ever holds the fixture project. (Done 17 October 2026: created, and the fixture project pushed to its default branch `main`.) Grindstone pushes to it, opens pull requests and sets statuses on it; it is never Grindstone's own repository, so tests cannot disturb real work (the dogfooding risk in the Roadmap).

Its ruleset: import `.github/rulesets/testbed-main.json`, then set the source of the required check `grindstone/verification` to the Grindstone App (after step 3). That source restriction is what makes the status unforgeable from inside the repository: a GitHub Actions workflow posting the same context must not satisfy it. SPK-4 verifies it.

Then attach the testbed to the Claude cloud environment (or start a session with it selected), so sessions can push the fixture project and run SPK-4.

## 3. Create the GitHub App (needed by SPK-4; M1 delivery)

Settings (your account) → Developer settings → GitHub Apps → New GitHub App:

| Field | Value |
| --- | --- |
| Name | `grindstone-dev-<suffix>` (App names are global) |
| Homepage URL | The repository URL |
| Webhook | **Off**. The outer loop polls (ADR-32), so nothing needs an inbound endpoint |
| Repository permissions | Contents: read and write · Pull requests: read and write · Commit statuses: read and write · Checks: read · Issues: read · Metadata: read |
| Account permissions | None |
| Where can it be installed | Only on this account |

Then generate a private key and install the App on **`ex1tium/grindstone-testbed` only**; it is added to `ex1tium/grindstone` at the end of M1, when Grindstone starts delivering its own tickets (M1-08). Keep these for step 5 (on a self-hosted machine they would be these files):

```
secrets/github_app_id               # the numeric App ID
secrets/github_app_installation_id  # from the installation URL
secrets/github_app_private_key.pem  # chmod 600
```

On a host, only the `grindstone` container will ever mount them (I-08, I-09). For cloud sessions, see step 5.

## 4. Agent credentials (needed by SPK-1, SPK-3, SPK-5)

- **Claude Code on your subscription** (ADR-18). Create a long-lived token for headless use with the Claude Code CLI, following the current Claude Code documentation; SPK-1 records the exact command and the full list of credential sources that would outrank it. Do not also provide `ANTHROPIC_API_KEY` to the same environment: an API key outranks the subscription.
- **No second provider for now** (ADR-41): Codex and SPK-3 are deferred until you add one.
- Set provider-side spend limits wherever an API key is used. With per-task budgets removed (ADR-37), the provider limit and the optional project cap are the spend ceilings.

## 5. Cloud environment (the spike host)

Spikes and day-to-day development run in Claude Code cloud sessions. The SessionStart hook (`.claude/hooks/session-start.sh`) installs Node and pnpm, syncs the locked dependencies, and starts Docker with a Docker Hub mirror and builds through the session proxy, so `make check`, `make up` and `make smoke` work in a fresh session. It takes effect for sessions started from `main` once merged.

In the environment's settings (the cloud environment menu in the session's title bar → Edit):

| Setting | Value | Needed by |
| --- | --- | --- |
| Environment variable `GRINDSTONE_CLAUDE_OAUTH_TOKEN` | The subscription token from step 4 | SPK-1, SPK-5 |
| Environment variables `GRINDSTONE_GITHUB_APP_ID`, `GRINDSTONE_GITHUB_APP_INSTALLATION_ID`, `GRINDSTONE_GITHUB_APP_PRIVATE_KEY_B64` | From step 3; the key is the `.pem` file base64-encoded on one line (`base64 -w0 key.pem` on Linux, `base64 -i key.pem` on macOS), because multi-line values do not survive every settings form | SPK-4 |
| Network access | Allow `github.com` and `api.github.com`, `ghcr.io`, `mirror.gcr.io`, `nodejs.org` | SPK-4, the hook |

The names are prefixed so the tools themselves never pick them up implicitly; spike code passes each one explicitly to the one process that needs it, mirroring how the containers scope secrets.

**What this trades.** The App's private key, which can push and set statuses on the testbed, and your subscription token now live in the hosted environment's settings rather than only on your own machine. That is acceptable while the App is installed on the testbed alone. Before the App is installed on `ex1tium/grindstone` (end of M1, M1-08), decide where the stable self-hosting instance runs and keep the production key there; the kickoff deferred that choice to the M1 review.

## Checklist

- [x] Ruleset imported on `ex1tium/grindstone` from `grindstone-main.json`; squash-only merges; head branches auto-deleted
- [ ] Code security features on
- [x] `ex1tium/grindstone-testbed` created and attached to this session
- [x] Testbed switched to public
- [ ] Testbed attached to the cloud environment for future sessions
- [x] GitHub App created, key generated, installed on the testbed only
- [x] Testbed ruleset imported from `testbed-main.json`, check source set to the App
- [x] Cloud environment: token and key variables, network allow-list
- [x] SessionStart hook merged to `main`
