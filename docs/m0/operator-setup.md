# Operator setup for M0

What only the operator can do, in the order the work needs it. Each step says which exit criterion or spike it unblocks. Secrets never enter this repository or a cloud session: they live on the operator's hosts, in files under `secrets/` (ignored by git) or in a password manager.

## 1. Protect `main` on `ex1tium/grindstone` (now)

Settings → Rules → Rulesets → New branch ruleset, targeting the default branch:

- Require a pull request before merging; allow **squash** merges only; require linear history.
- Require status checks to pass, with the branch up to date before merging: `Lint, types, tests, fitness functions` and `Compose smoke test (M0-01)`. Both appear in the picker after the first CI run on a pull request.
- Block force pushes and deletions.
- Bypass: none. The operator's plain pull requests that touch no published file stay possible (ADR-33), but they go through CI like everything else.

Settings → Code security: turn on Dependabot alerts and security updates, secret scanning and push protection.

## 2. Create the GitHub test repository (M0-04; needed by SPK-4)

Create **private** `ex1tium/grindstone-testbed`, initialised with a README. Grindstone pushes to it, opens pull requests and sets statuses on it; it is never Grindstone's own repository, so tests cannot disturb real work (the dogfooding risk in the Roadmap).

The fixture project inside it (a small Python package with tests annotated `@verifies AC-…`) is committed by the first M0-04 task; you only create the empty repository.

Its ruleset (Settings → Rules → Rulesets, default branch):

- Require a pull request; require status checks with the branch up to date.
- Required check: `grindstone/verification`, with **its source restricted to the Grindstone App** (after step 3). This is what makes the status unforgeable from inside the repository: a GitHub Actions workflow posting the same context name must not satisfy it. SPK-4 verifies that.
- Block force pushes and deletions.

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

Then generate a private key and install the App on **`ex1tium/grindstone-testbed` only**; it is added to `ex1tium/grindstone` at the end of M1, when Grindstone starts delivering its own tickets (M1-08). Keep these on the host that runs the spikes:

```
secrets/github_app_id               # the numeric App ID
secrets/github_app_installation_id  # from the installation URL
secrets/github_app_private_key.pem  # chmod 600
```

Only the `grindstone` container will ever mount them (I-08, I-09).

## 4. Agent credentials (needed by SPK-1, SPK-3, SPK-5)

- **Claude Code on your subscription** (ADR-18). On the spike host, sign in with the Claude Code CLI and create a long-lived token for headless use, following the current Claude Code documentation. SPK-1 records the exact command, how the token is supplied, and the full list of credential sources that would outrank it. Store it as `secrets/claude_oauth_token`. Do not also set `ANTHROPIC_API_KEY` in that environment: an API key outranks the subscription.
- **Codex** (Q-3). SPK-3 first tries subscription login headless in a container. Have an OpenAI API key ready as the fallback, with a monthly spend limit set in the OpenAI dashboard; store it as `secrets/openai_api_key`.
- Set provider-side spend limits wherever an API key is used. With per-task budgets removed (ADR-37), the provider limit and the optional project cap are the spend ceilings.

## 5. The spike host

The spikes need Docker, the credentials above, and real agent sessions. Run them on your own server:

- Linux with Docker Engine and Compose, 8 cores, 32 GB memory and 500 GB disk (the capacity assumption checked at the M3 review).
- Docker Hub pulls authenticated (`docker login`), or a pull-through mirror: anonymous pulls are rate-limited per IP.
- A clone of this repository, `make setup`, and `make smoke` passing first.
- VS Code on a machine that can reach the host, for the attach test in SPK-1.

Each spike's plan in `docs/spikes/` lists its steps, what to record and its pass criteria; a Claude Code session on that host can run a plan and file the report.

## Checklist

- [ ] `main` ruleset on `ex1tium/grindstone`, with both CI checks required
- [ ] Code security features on
- [ ] `ex1tium/grindstone-testbed` created (private)
- [ ] GitHub App created, key generated, installed on the testbed only
- [ ] Testbed ruleset requiring `grindstone/verification` from the App
- [ ] Claude subscription token on the spike host
- [ ] OpenAI API key with a spend limit, as the Codex fallback
- [ ] Spike host ready: Docker, authenticated pulls, `make smoke` green
