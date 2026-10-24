# SPEC-05 — Deployment, users and secrets
Status: accepted (by the operator, 19 October 2026, after the reviews in `docs/specs/reviews/`); amended 24 October 2026 with foundation v4.11 and v4.12 (ADR-55, ADR-57, ADR-58: open agent egress, the `sessions` volume, REQ-0515) · Milestone: M1
Kind: kernel · Owns: the Compose deployment (`compose.yaml`, the four images and their entrypoints, `deploy/grindstone.toml`, secret provisioning), Unix users and file layout on the shared volumes, container capabilities, listeners and network rules, the Claude agent preset's launcher and credential self-test, and the agent host's people directory

Compact walking-skeleton specification (Planning playbook). Review: by a session that did not write it, then the operator.

## 1. Purpose

Authority lives only in the control plane; work runs on stations that hold nothing that could forge evidence or ship code (I-09, ADR-01, ADR-17). This specification makes that true of the running deployment rather than of a diagram:
- which container holds which secret, readable by which Unix user;
- which capabilities each process keeps;
- how agents run as their own users in workspaces that no other agent and no host token can be read from;
- how a repository's settings are kept out of every session;
- how an agent dies with its host.

SPK-1 measured each of these; this specification fixes them for M1, and its tests run against the real images on every commit.

## 2. Scope

In scope:
- The four services and their images, users, groups, capabilities, entrypoints, networks, listeners and volumes.
- Secrets: what exists, where each lives, who can read it, how it is provisioned and rotated.
- File layout and modes on `workspaces`, `runs` and the session configuration area.
- The Claude agent preset's launcher: credential self-test, settings sources off, the fixed security floor of Claude Code options.
- The agent host's people directory and viewer grants.
- Making agents die with their host.
- The instance configuration file shipped for Compose.
- The deployment and workspace-mount lints (FF-05, FF-06).
- The M1-05 security tests.

Out of scope:
- **Several agent accounts** (ADR-48, foundation v4.10): SPEC-17 (M3) adds one credential secret per account and gives each session only its own. M1 provisions the one `claude_oauth_token`.
- The host's control API, backend wrapper, sessions, events and the scripted agent preset: SPEC-06.
- How grindstone writes and reads workspaces through the workspace provider, copy-back tiers and hooks in the control plane: SPEC-06 and SPEC-09.
- The operator login flow: SPEC-10. This specification provisions its secret.
- Exposing AHP to browsers and VS Code: SPEC-22 (M4). In M1 the host's AHP listener serves loopback only.
- Backup, restore, upgrade and rotation runbooks: SPEC-27. This specification states the rotation rule.
- Egress restricted per project: committed to no release; it needs an egress proxy, a new component with its own record (ADR-55, ADR-57).

## 3. Foundation links

Implements:
- ADR-01: one control plane and three supporting containers; five volumes mounted only where allowed, the fifth being the agent host's `sessions` (ADR-58); images pinned by digest.
- ADR-55, as amended by ADR-57: agent egress is open at T1; the Claude preset maps the `web` category; the runner has no network.
- ADR-17: T1 agent stations run agents under their own Unix user; no station holds a control-plane credential.
- ADR-42: the host uses its packages unmodified; a vendored launcher in front of the agent's ACP adapter runs the credential self-test and turns every settings source off; the host has a people directory so that viewers never answer permission requests.
- ADR-18 (as amended by ADR-41): Claude on the operator's own subscription, guarded at start-up against every credential that would outrank it; repository hooks, settings and MCP servers kept out of sessions; an API key is configuration only.
- ADR-39: start skills are materialized into the session's private configuration directory outside the workspace.
- I-09: credentials split by container and purpose; the control plane never executes work content; nothing mounts the Docker socket.
- I-14: configuration is unreachable from any workspace.
- QS-03, QS-06: credentials unreadable from stations; repository settings never reach a session.

Delivers:
- M1-05, these clauses:
  - "From `agent-host` and `runner` no GitHub, database or MCP signing credential is readable and a push to GitHub fails" → AC-0503-1, AC-0503-2.
  - "nothing mounts the Docker socket" → AC-0501-1.
  - "repository settings never reach a session" → AC-0508-1, AC-0508-2.
  - "deployment and workspace mount lints (FF-05, FF-06) pass" → AC-0501-1, AC-0510-1.
- SPEC-09 delivers the clauses on hooks in the control plane and copy-back tiers.

Depends on:
- SPEC-02: `StoreSettings`.
- SPEC-03: the instance configuration file and its `[secrets]` and `[images]` sections.

Scenarios: K1 step 3 (dispatch to a T1 agent station); S1's session runs as its own user in its own workspace.

## 4. Requirements

REQ-0501: `compose.yaml` runs exactly `postgres`, `grindstone`, `agent-host` and `runner`, every image pinned by digest, with volumes mounted only as ADR-01 allows, no Docker socket and no host path other than secret files and the instance configuration.
REQ-0502: Each secret is a file on the host, readable only by its owner there, mounted only into the containers in the secret table, and inside each container readable only by the one service user that needs it.
REQ-0503: No file, environment variable or process attribute readable by an agent user or by `gs-runner` yields the database password, a GitHub credential, the MCP token key, the host control key, the host event key, the operator session key or the operator password hash.
REQ-0504: Every service process runs as its own non-root user with an empty capability set, except the agent host, which keeps exactly `CAP_SETUID` and `CAP_SETGID`, and `postgres`, which keeps its official image's defaults; a container's entrypoint holds more only until it hands secrets to its service user, and then drops them.
REQ-0505: Each run's sessions run as the agent user the run is bound to (SPEC-06 part 1), from a pool of agent users per station in which no two unfinished runs share one, with no capabilities, umask 027, no membership of a shared group, and a working directory under its own user's subtree of `workspaces`.
REQ-0506: No agent user can list the workspaces root, read another agent user's subtree or session directories, or read the staging area; the control plane and the host can read every run directory but cannot write into one.
REQ-0507: An agent process does not outlive its host: the host runs under an init that stops the container when the host exits, and each agent is started with a parent-death signal.
REQ-0508: The Claude preset's launcher starts every session with no settings source, never in bare mode, with `CLAUDE_CONFIG_DIR` and `HOME` set to the session's private configuration directory outside `workspaces`, so no hook, setting, MCP server, `CLAUDE.md` or skill from a workspace takes effect.
REQ-0509: The launcher's credential self-test refuses to start a session when the subscription token is missing, when any credential source that outranks it is present, when a managed-settings file exists, or when the private configuration directory holds a login or a settings key that selects credentials.
REQ-0510: No configuration path (the instance file, secrets, factory packages, the session configuration area) is mounted in or under a workspace or run directory, and the host refuses a session configuration directory under `workspaces`.
REQ-0511: The agent host is configured with a people directory in which only the control plane's principal may answer a permission request; a viewer principal is refused `chat:answer`.
REQ-0512: The control plane serves operators and stations on separate listeners: the operator listener (published on loopback) refuses connections from the stations' network, and the station listener serves only the kernel MCP surface and the host event endpoint.
REQ-0513: `make secrets` creates every secret the deployment needs with mode 0600 in a 0700 directory, never overwriting one that exists, and records the operator password only as an Argon2 hash.
REQ-0514: An entrypoint refuses to start when a mounted secret is readable by anyone but its owner on the host.
REQ-0515: The Claude preset maps the `web` permission category to allowing Claude Code's web search and fetch tools, and a session without `web` gets both in its denied tools rather than left to a permission prompt (ADR-55).

## 5. Design

**Users and groups** (numeric IDs fixed across images, because the volumes are shared):

| Name | UID / GID | In container | Groups | Purpose |
| --- | --- | --- | --- | --- |
| `grindstone` | 10001 | `grindstone` | `gs-workspaces`, `gs-runs` | Control plane |
| `gs-host` | 10002 | `agent-host` | `gs-workspaces` | Agent host process |
| `gs-runner` | 10003 | `runner` | `gs-runs` | Check jobs |
| `gs-workspaces` | 10100 (group) | `grindstone`, `agent-host` | — | Read access to run directories |
| `gs-runs` | 10200 (group) | `grindstone`, `runner` | — | Job directories |
| `gs-agent-1` … `gs-agent-8` | 10201–10208 | `agent-host` | own group only | The station's pool: each bound to one run for the run's life (SPEC-06 part 1, DEC-0606); a larger pool means more users in the image |

**File layout on `workspaces`** (from SPK-1, experiment 1):

| Path | Owner : group | Mode | Who writes |
| --- | --- | --- | --- |
| `/var/lib/grindstone/workspaces` | `root:gs-workspaces` | 2771 | Nobody lists; members create `staging` |
| `…/staging/` | `grindstone:gs-workspaces` | 2750 | The control plane writes one archive per run (0640); the host reads it; agents cannot |
| `…/agents/<agent>/` | `<agent>:gs-workspaces` | 2750 | Created by the agent-host entrypoint |
| `…/agents/<agent>/<run>/` | `<agent>:gs-workspaces` | 2750 | The agent, through the host's helper (TKT-0502): the host, a member of `gs-workspaces`, reads the staging archive and streams it to an extractor running as the agent user, who cannot open the archive itself; written by the agent, read by the control plane, removed as the agent user |

Run directories are named by run ID (UUIDv7) under the subtree of the agent user the run is bound to (`agents/<user>/<run>/`, SPEC-06 part 1, DEC-0606). The setgid bit keeps every file in group `gs-workspaces`, and umask 027 keeps it group-readable and closed to others. An agent that makes a file unreadable to the group only makes its own collect fail (SPEC-09).

**`runs`.** `root:gs-runs` 2770. The control plane writes job directories (subject 0750 and read-only to the runner by mode; `out/` 2770). This follows the M0 runner image and M0-04's fixture check.

**Session configuration area** (agent host only): the volume `sessions` at `/var/lib/grindstone/sessions`, mounted in `agent-host` alone, with one directory per agent user (`<agent>`, 0700). It survives a host restart, which restarts the container, so a lost session can be resumed within the resume window; the host removes a session's directory with the session and sweeps lost sessions' directories whose last event is older than the window (REQ-0631, ADR-58). Under it the host's helper creates, as the agent user, `<run>/<session>/` as that session's `CLAUDE_CONFIG_DIR` and `HOME` (ADR-39), so a restarted host finds a run's directories by its run ID.

| Path | Owner : group | Mode | Who writes |
| --- | --- | --- | --- |
| `/var/lib/grindstone/sessions` | `root:root` | 0711 | The agent-host entrypoint sets the mode; no agent user can list it |
| `…/.host/` | `gs-host:gs-host` | 0700 | Created by the agent-host entrypoint; the host's event markers (SPEC-06 part 1) |
| `…/<agent>/` | `<agent>:<agent>` | 0700 | Created by the agent-host entrypoint |
| `…/<agent>/<run>/` | `<agent>:<agent>` | 0700 | The host's helper, as the agent user |
| `…/<agent>/<run>/<session>/` | `<agent>:<agent>` | 0700 | The agent, through the host's helper; removed as the agent user |

Start skills are copied into a session's directory read-only (files 0444, directories 0555). M1 capabilities have none.

**Capabilities and entrypoints.** Every container keeps `no-new-privileges`. Every container but `postgres` also keeps a read-only root, `cap_drop: ALL` and `/tmp` on tmpfs. `postgres` is the one exception: its official entrypoint needs its default capabilities to read its operator-owned secret and to own its data directory, so it keeps the image defaults with a writable root and its data volume, as in M0. It runs no work content and is reachable only on `db`.

| Service | Entrypoint (as root) adds | Service process runs as | Keeps |
| --- | --- | --- | --- |
| `postgres` | The official image's entrypoint (unchanged) | `postgres` | Image default |
| `grindstone` | `DAC_READ_SEARCH`, `SETUID`, `SETGID`: copy secrets into `/run/gs` (tmpfs, `grindstone`, 0700), then `setpriv` to `grindstone` with an empty bounding set | `grindstone` | Nothing |
| `agent-host` | `DAC_READ_SEARCH`, `CHOWN`, `SETUID`, `SETGID`: copy secrets into `/run/gs-host` (tmpfs, `gs-host`, 0700); create `agents/<agent>/`, `/var/lib/grindstone/sessions/<agent>/` and `sessions/.host/`; check that no process of an agent user runs; then `setpriv` to `gs-host` with bounding, inheritable and ambient sets of `SETUID` and `SETGID` only | `gs-host` | `CAP_SETUID`, `CAP_SETGID` (SPK-1) |
| `runner` | None: no secrets | `gs-runner` | Nothing |

The entrypoints are POSIX shell scripts of a few lines in `docker/entrypoints/`. `agent-host` runs with `init: true`, Docker's init as PID 1 with the entrypoint and then the host as its only child, so the container stops when the host exits, killing every agent with it (REQ-0507). The host's helper also starts each agent with `setpriv --pdeathsig=KILL`. The start-up check for leftover agent processes finds none in a fresh PID namespace; it guards against a future change that drops the init.

**Secrets.**

| Secret file (`secrets/`) | Mounted in | Readable inside by | Used for |
| --- | --- | --- | --- |
| `postgres_password` | `postgres`, `grindstone` | the `postgres` entrypoint; `grindstone` | Database |
| `mcp_token_key` | `grindstone` | `grindstone` | Signing per-task MCP tokens (SPEC-07) |
| `host_control_key` | `grindstone`, `agent-host` | `grindstone`; `gs-host` | Bearer for the host control API (SPEC-06) |
| `host_event_key` | `grindstone`, `agent-host` | `grindstone`; `gs-host` | HMAC on host events (SPEC-06) |
| `session_key` | `grindstone` | `grindstone` | Operator session cookies (SPEC-10) |
| `operator_password_hash` | `grindstone` | `grindstone` | Argon2 hash of the operator password (SPEC-10) |
| `github_app_key` | `grindstone` | `grindstone` | The GitHub App's private key: a factory secret granted per project (SPEC-03, SPEC-09) |
| `claude_oauth_token` | `agent-host` | `gs-host`, then each Claude agent's environment | Model credential; readable by agents by design (Threat model, residual risks) |

The GitHub App ID and installation ID are not secrets. They are configuration in the project's factory section (SPEC-09).

How secrets are handled:
- **Mounting.** Compose mounts file secrets with their host ownership and mode: "when the source is a file, Compose uses a bind-mount under the hood which doesn't allow uid remapping, and these attributes [`uid`, `gid`, `mode`] are silently ignored" (Docker documentation, Compose file reference, services, `secrets`, read 18 October 2026). The files are 0600 and owned by the operator, so no container user can read the mounted copy; only the entrypoint, with `DAC_READ_SEARCH`, copies each into its service user's private tmpfs before dropping the capability (DEC-0501). `[secrets]` in `grindstone.toml` names the copies, for example `/run/gs/github_app_key`.
- **Provisioning (REQ-0513).** `make secrets` replaces M0's `dev-secrets.sh`. It generates the random keys (32 bytes, base64url) and prompts once for the operator password, storing its Argon2id hash. The parameters are this specification's: RFC 9106's second recommended option (64 MiB, 3 passes, 4 lanes), which SPEC-10 reads from the hash itself when it verifies. The hash is computed by `uv run --frozen python -m scripts.hash_password`, which reads the password from the terminal without echo, never from argv or the environment, and uses `argon2-cffi==25.1.0` (PyPI, released 3 June 2025, the latest; its bindings 26.1.0 ship abi3 wheels for CPython 3.14), pinned by this specification and used by SPEC-10 to verify. It asks for the paths of the GitHub App key and the Claude token and copies them in. It never overwrites an existing file.
- **Rotation.** Replace the file, then restart every container the table lists for it. The host keys need `grindstone` and `agent-host` together.

**The Claude preset's launcher** (`agent-host/presets/claude/`; a preset is the host's configuration for one agent runtime, so nothing Claude-specific enters the host core, ADR-41). Started by the host's helper as the agent user:
1. Run the credential self-test (REQ-0509). The list is SPK-1's, from the Claude Code documentation of 17 October 2026:
   - `CLAUDE_CODE_OAUTH_TOKEN` must be present;
   - none of the 27 provider, credential, route and gateway variables may be set;
   - no managed-settings file or directory (`/etc/claude-code/managed-settings.json`, `managed-settings.d/`, `managed-mcp.json`) may exist;
   - `CLAUDE_CONFIG_DIR` must be set and outside `workspaces`;
   - no stored login, and no `settings.json` setting `apiKeyHelper`, `env`, a `forceLogin*` key or `allowedProviders`, in the configuration directory.
   The list is a data file beside the launcher, with the adapter version it was read for. A test fails when the pinned adapter version changes and the list's version does not, so the list is re-read on every adapter upgrade (Risks table).
2. Start the unmodified `claude-agent-acp` behind a stdio proxy that merges into the `_meta.claudeCode.options` of every `session/new`, load, resume and fork:
   - the **security floor**, which the per-session options from SPEC-06 part 1 cannot override: `settingSources: []`, no bare mode (the token is not read in bare mode), and `disallowedTools` including `Skill` when the capability has no start skills;
   - and those per-session options, mapped from SPEC-06 part 1's agent-neutral `SessionOptions`: `model` and `effort` to Claude Code's model options, permission categories to its tool rules, `read_only` to denying its file-writing tools, and `tool_timeout_seconds` to `MCP_TOOL_TIMEOUT` in the agent's environment allow-list (SPK-5). Only this preset names those settings.

SPK-1, experiment 5, showed that with this floor a hostile workspace's `.claude/settings.json` hooks, `env` block, `.mcp.json`, `CLAUDE.md` and skills all stay inert. A repository's `CLAUDE.md` reaches an agent only as a pinned item in its context pack, recorded on the run (SPK-1's decision).

**People directory (REQ-0511).** The host is created with a `users` directory, which the AHP SDK needs before it checks grants at all (SPK-1, experiment 7). It holds two principals:
- the control plane, whose root token is `host_control_key`, with every grant;
- a viewer role, with `config:settings`, `session:state`, `chat:turns` and `chat:send` but never `chat:answer`.

In M1 the AHP listener binds loopback only and no viewer token is issued. Loopback inside `agent-host` is shared with every agent process in the same network namespace, so the address protects nothing: the people directory and its tokens are the protection, and an agent connecting without a token is refused. SPEC-22 issues viewer tokens to the UI and VS Code after login. The refusal is tested now, in-container.

**Listeners and networks.** The M0 networks stay as they are:
- `db` (internal) carries `postgres` and `grindstone`;
- `agents` (internal) carries `grindstone` and `agent-host`;
- `control-egress` carries `grindstone`, to GitHub;
- `agent-egress` carries `agent-host`, with open egress at T1 (ADR-55);
- `runner` is on no network in M1 (DEC-0505): its toolchain image carries the project's dependencies, as the Risks table's "dependencies baked into the toolchain image" says and as M0-04's fixture check already runs, and the M0 `runner-egress` network is removed.

Compose gives each a fixed subnet. `grindstone` serves two listeners (REQ-0512):
- **operator**, `:8080`, published as `127.0.0.1:8080`. It serves REST, the event stream and the UI (SPEC-10), and refuses any peer in the `agents` or `db` subnet.
- **stations**, `:8081`, never published. It serves only `/kernel/mcp` (SPEC-07) and `/stations/host/events` (SPEC-06).

`agent-host` serves its control API on `:8090` on `agents` (bearer `host_control_key`) and AHP on loopback. The runner listens on nothing.

**Instance configuration.** `deploy/grindstone.toml` is mounted read-only at `/etc/grindstone/grindstone.toml` in `grindstone` only. It is the file SPEC-03 reads, with the sections SPEC-02, SPEC-03, SPEC-06 and SPEC-10 own. It names the secret copies, the allowed check images by digest, and one agent station and one check station.

**Where M1's real delivery runs** (decided by the operator for the M1 review). Default: the operator's own machine, with Docker Desktop on WSL2 running the four Linux containers, the repository and `secrets/` on the WSL2 Linux filesystem, and the GitHub App key only there. A cloud session can never act as the App (SPK-4). REQ-0514's entrypoint check fails closed if `secrets/` sits on a filesystem that shows every file as world-readable, as Windows drives mounted into WSL2 do.

**Security tests (M1-05)**, run by `make smoke` against the built stack:
- From each agent user (through `docker compose exec` with `setpriv`, as the host would) and from `gs-runner`: try to read every path in the secret table, every file under `/run`, `/etc/grindstone`, the other agents' subtrees and session directories, the staging area, and `/proc/<pid>/environ` and `/proc/<pid>/cmdline` of every other process; dump their own environment. Each attempt must fail, and no secret's value may appear in anything read, compared by its SHA-256 so the test itself never prints a secret.
- From the same users: `git push` over HTTPS to the test repository must fail with an authentication error.
- From `agent-host`: connect to `postgres:5432` and to `grindstone:8080`; both are refused. The control API without the key gets 401.
- The launcher, in front of a stub ACP adapter that records what it receives, passes the security floor on every session it opens. The testbed's hostile-repository fixture (`fixtures/hostile/`), placed at its real paths in a workspace, takes no effect in the recorded live run at the M1 close.

**Interfaces.** `make secrets`, `make up`, `make smoke`. Entrypoint scripts. The launcher's self-test as a command (`selftest`) for diagnosis.

**Configuration.** `deploy/grindstone.toml` and `compose.yaml`. Only the operator changes either, and restarts the affected containers.

**Make and prove.** No subjects. The deployment is proven by the smoke and security tests, which run against the images CI builds, not against a description of them.

**Fitness functions.**
- FF-05 is added. It reads `compose.yaml` and fails when:
  - a secret is mounted in a container not listed for it in the secret table (kept as data in `scripts/ff/deployment.py`);
  - a station mounts `blobs` or `repos`;
  - anything mounts the Docker socket or a host path other than secrets and the instance file;
  - a service but `postgres` lacks `cap_drop: ALL` and a read-only root, or adds a capability outside the entrypoint table;
  - `runner` is attached to any network;
  - `agent-host` lacks `init: true`;
  - the `sessions` volume is mounted in any service but `agent-host`;
  - a published port binds anything but loopback.
- FF-06 is added. It fails when:
  - a volume or bind that holds configuration (the instance file, secrets, factory packages) is mounted in `agent-host` or `runner`;
  - `workspaces` or `runs` is mounted at or above a configuration path;
  - the host's configured session area lies under the workspaces root, or `sessions` is mounted at or under a workspace path.

## 6. Decisions

DEC-0501: Secret files are 0600 on the host and copied by a root entrypoint holding only `DAC_READ_SEARCH` (with `SETUID`, `SETGID`, and `CHOWN` for the host's directories) into the service user's private tmpfs, before the capabilities are dropped · Compose mounts file secrets with host ownership and silently ignores per-secret owner and mode (Docker documentation, cited in section 5), so a mounted copy readable by the service user would also be readable by every agent in the same container · Rejected: world-readable mounted secrets, as in M0 (agents in `agent-host` could read the host keys); requiring the operator to `chown` secrets to container UIDs (a manual, host-specific install step); secrets in environment variables (`@ahpd/agent-acp` merges an agent's environment over the host's, so they would leak into agents, as SPK-1 found); Compose secrets sourced from the environment, for which Compose does apply `uid`, `gid` and `mode` (the secrets would have to live in Compose's environment, a `.env` file or the operator's shell, and the multi-line App key would need encoding, for no gain in protection over a 0600 file).
DEC-0502: A pool of agent Unix users per station, each bound to one run for its life, with workspaces under that user's own subtree · Concurrent runs never share a UID, a suspended run keeps its workspace without holding a lane, and an agent can create its run directory without any capability · Rejected: one agent user for all sessions (concurrent runs could read each other's workspaces); a user per run (needs `useradd` at run time, that is, root).
DEC-0503: Docker's init as PID 1 with the host as its only child, plus a parent-death signal per agent · SPK-1, experiment 8, showed an orphaned Claude Code process writing after its host died; the init also reaps orphaned grandchildren, which the host as PID 1 would not · Rejected: the host as PID 1 (zombie processes accumulate); parent-death signal alone (a grandchild that re-parents survives).
DEC-0504: The launcher's security floor overrides per-session options · Repository configuration must never reach a session, whatever a capability asks for (ADR-18) · Rejected: trusting capability files to set `settingSources` (one wrong capability file would load repository hooks).
DEC-0505: The runner has no network in M1 · Checks must be repeatable from the subject and the image, and code under test then cannot reach anything; Compose cannot restrict a network to package registries, so `runner-egress` was open egress in fact · Rejected: open egress for the runner (code under test reaches the internet, and results can depend on what a registry serves that day); an egress proxy (a new component, OQ-0502). A ticket that changes a project's dependencies needs its toolchain image rebuilt by the operator before its checks can pass, and its evidence names the new image digest (SPEC-08's environment fingerprint).

## 7. Tickets and acceptance criteria

TKT-0501: Images, users, entrypoints, compose (with the runner off every network), `make secrets` and `scripts/hash_password.py`, instance file · implements REQ-0501, REQ-0502, REQ-0504, REQ-0512 to REQ-0514 · depends on TKT-0303 · paths `compose.yaml`, `docker/`, `deploy/`, `scripts/make_secrets.sh`, `scripts/hash_password.py`, `pyproject.toml` (argon2-cffi), `Makefile`.
TKT-0502: Workspace and session layout, and the host's helper that runs a command as an agent user (`spawnAsAgent` with umask 027 and a parent-death signal, `stopAll(user)`, which runs `kill -KILL -1` as that user and waits until `/proc` lists none of its processes, archive extraction, removal, session directories), which SPEC-06 part 1's host core uses · implements REQ-0505 to REQ-0507, REQ-0510 · depends on TKT-0501 · paths `docker/entrypoints/`, `agent-host/src/helper/`.
TKT-0503: Claude preset launcher, security floor and credential self-test · implements REQ-0508, REQ-0509, REQ-0515 · depends on TKT-0501 · paths `agent-host/presets/claude/`, `agent-host/test/`, `agent-host/package.json`.
TKT-0504: People directory and viewer grants, tested on `createHost` from `@ahpd/sdk` with a stub backend, so it does not wait for SPEC-06's host core · implements REQ-0511 · depends on TKT-0501 · paths `agent-host/src/people.ts`, `agent-host/test/`.
TKT-0505: FF-05, FF-06 and the M1-05 security tests in `make smoke` · implements REQ-0501, REQ-0503, REQ-0510 · depends on TKT-0502, TKT-0503 · paths `scripts/ff/`, `scripts/compose_smoke.py`, `tests/fitness/`.

AC-0501-1: FF-05 passes on `compose.yaml`, and fixtures with a Docker socket mount, `blobs` on a station, an unlisted secret mount, an extra capability and a non-loopback published port and the `sessions` volume mounted in `grindstone` each fail it · verifies REQ-0501 · contract · `test_ff05_deployment_lint`.
AC-0502-1: Inside each container but `postgres`, every mounted secret's original under `/run/secrets` is unreadable by the service user, and its copy is readable only by the user the secret table names; the `runner` container has no network interface but loopback · verifies REQ-0502 · security · `test_secrets_readable_only_by_their_user`.
AC-0503-1: From each agent user and from `gs-runner`, every read the security test attempts fails, and no secret's SHA-256 matches anything read or any environment value · verifies REQ-0503 · security · `test_no_control_credential_reachable_from_stations`.
AC-0503-2: From each agent user and from `gs-runner`, `git push` to the test repository fails with an authentication error · verifies REQ-0503 · security · `test_push_from_stations_fails`.
AC-0504-1: The capability sets in `/proc/<pid>/status` are empty for the `grindstone`, `gs-runner` and agent processes, and exactly `CAP_SETUID` and `CAP_SETGID` for the host · verifies REQ-0504 · security · `test_process_capabilities`.
AC-0505-1: Two agents started concurrently through the helper for two bound runs run as different agent users, each with umask 027, no capabilities and no supplementary groups · verifies REQ-0505 · security · `test_concurrent_agents_have_distinct_users`.
AC-0506-1: An agent user cannot list the workspaces root, read another agent's subtree or `/var/lib/grindstone/sessions/<other agent>/`, or open the staging area or its own run's archive; `grindstone` and `gs-host` can read a run directory and cannot create a file in it · verifies REQ-0506 · security · `test_workspace_layout_isolation`.
AC-0507-1: After SIGKILL of the host process while a stub agent started through the helper is about to write a file, the container restarts, no process of any agent user exists, and the file never appears · verifies REQ-0507 · security · `test_agents_die_with_host`.
AC-0508-1: In front of a stub ACP adapter that records its input, the launcher sets `settingSources: []`, a private `CLAUDE_CONFIG_DIR` and `HOME` outside `workspaces`, and no bare mode on every `session/new`, load, resume and fork, and overrides a per-session option asking for `settingSources: ["project"]` · verifies REQ-0508 · contract · `test_launcher_security_floor`.
AC-0515-1: In front of the stub ACP adapter, a session whose options allow `web` gets tool rules allowing web search and fetch, and a session without it has both in its denied tools · verifies REQ-0515 · contract · `test_web_category_mapping`.
AC-0508-2: Live run: with the testbed's hostile fixtures at their real paths in a workspace, a Claude Code session through the launcher runs none of their hooks, sets none of their environment, starts none of their MCP servers, and loads neither the `CLAUDE.md` nor the skill · verifies REQ-0508 · live run · `live_m1_05_hostile_repository`.
AC-0509-1: The self-test fails with each listed credential source set in turn, with a managed-settings file present, and with a stored login in the configuration directory, and passes with none · verifies REQ-0509 · unit · `test_credential_selftest`.
AC-0509-2: Changing the pinned adapter version without updating the self-test list's version fails the test suite · verifies REQ-0509 · unit · `test_selftest_list_tracks_adapter_version`.
AC-0510-1: FF-06 passes, and fixtures mounting the instance file into `agent-host`, `workspaces` over `/etc/grindstone`, a session area under the workspaces root and `sessions` mounted under a workspace path each fail it · verifies REQ-0510 · contract · `test_ff06_workspace_mount_lint`.
AC-0511-1: A viewer principal's permission answer is refused by the host and nothing runs; the control plane's answer is honoured; an agent user connecting to the AHP listener on loopback without a token is refused · verifies REQ-0511 · integration · `test_viewer_cannot_answer_permission`.
AC-0512-1: A request to `:8080` from `agent-host` is refused; `/kernel/mcp` and `/stations/host/events` are not served on `:8080`; REST is not served on `:8081` · verifies REQ-0512 · security · `test_listeners_are_separated`.
AC-0513-1: `make secrets` on an empty directory creates every secret 0600 in a 0700 directory, with the password stored only as an Argon2id hash; run again, it changes nothing · verifies REQ-0513 · unit · `test_make_secrets_idempotent`.
AC-0514-1: An entrypoint given a secret file with mode 0644 exits non-zero naming the file, and does not start its service · verifies REQ-0514 · unit · `test_entrypoint_refuses_readable_secret`.

## 8. Test plan

- Security, against the built stack in `make smoke` (CI job "Compose smoke test"): AC-0502-1, AC-0503-1, AC-0503-2, AC-0504-1, AC-0505-1, AC-0506-1, AC-0507-1, AC-0512-1.
- Contract: AC-0501-1 and AC-0510-1 (fitness fixtures), AC-0508-1 and AC-0515-1 (stub adapter).
- Live run at the M1 close, kept with its logs: AC-0508-2.
- Unit: AC-0509-1, AC-0509-2, AC-0513-1, AC-0514-1.
- Integration, `createHost` in-container with a stub backend: AC-0511-1.

## 9. Open items and risks

OQ-0501: Does Docker Desktop on WSL2, the default M1 delivery host, present 0600 secret files to containers with their ownership, so that only `DAC_READ_SEARCH` reads them? · Default: yes, when `secrets/` is on the WSL2 Linux filesystem; REQ-0514 fails closed otherwise · Resolved by TKT-0501, run once on the operator's machine.
OQ-0502: Should agent egress be limited to model providers and the project's granted package registries in M1? · Resolved by the operator (24 October 2026, ADR-55): no; `agent-egress` is open, as the Threat model's accepted residual risk allows at T1, and agents may search and read the web through capabilities holding the `web` permission (SPEC-09's implementer does; reviewers do not by default). The runner keeps no network (DEC-0505).
OQ-0503: Is a pool of eight agent users per station right? · Default: yes: one writing and four read-only lane slots (the capacity envelope) plus room for three runs suspended on the operator · Resolved by SPEC-06 part 1's OQ-0604 at the M1 review; a larger pool adds users in the image.

Risks mitigated: credential theft from stations (secret table, capability sets, tests on real images); repository-borne execution in sessions (launcher floor); orphaned agents acting after their host died (init and parent-death signal); a viewer answering permission requests (people directory).
Risks added:
- Session transcripts persist on the `sessions` volume (ADR-58) and can hold the model credential an agent printed. Mitigation: only `agent-host` mounts it, each agent user's directories are 0700, and the host disposes them with the session or run and sweeps lost ones after the resume window.
- Entrypoints run as root briefly. Mitigation: a few lines each, holding only the capabilities listed; FF-05 refuses any other.
- Agents can read the Claude token in their own environment. This is accepted at T1 (Threat model), and mitigated by per-provider spend limits and the rotation rule.

## 10. Rollout

`compose.yaml`, the Dockerfiles and `scripts/dev-secrets.sh` change. An M0 checkout runs `make secrets` once. It creates the new files and tightens existing ones to 0600, with confirmation. No stored data exists before M1. The M0 smoke test's volume, mount and network checks stay and gain the security tests above.
