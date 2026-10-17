# SPK-1 — Host, Claude and VS Code

Status: done; the VS Code half of experiment 6 is deferred to M4 (SPEC-22) by the operator · Box: 2 days · Settles: Q-1, Q-2, Q-6; the Claude credential-precedence list (M0-03); the assumption that an AHP host on `@ahpd/sdk` can run Claude Code sessions with a per-session MCP server (Architecture, "Constraints, assumptions and capacity")

## Why

ADR-15 builds the agent station as a thin host on `@ahpd/sdk`, with a vendored ACP agent plugin, driven by a typed control API. Everything in M1 that touches an agent rests on it, and the ecosystem is young: `@ahpd/sdk` is at 0.12.0 with releases every few days (`docs/m0/versions.md`).

## Known before starting

From the `@ahpd/sdk` 0.12.0 README (npm, 17 October 2026):

- `createHost({ path, agents, ... })` with agents passed in; `@ahpd/agent-claude` (a direct Claude backend) and `@ahpd/agent-acp` (an ACP bridge) are separate packages. ADR-15 means the ACP route: `@ahpd/agent-acp` with `@agentclientprotocol/claude-agent-acp`.
- The `mcpServers` option is **host-wide**: "the MCP servers every session is offered". Grindstone needs one MCP server, with its own bearer token, **per session** (ADR-16). This is the patch Q-1 anticipates; experiment 2 decides its shape.
- The package depends on `@microsoft/agent-host-protocol` ^1.0.0, although its README badge still says AHP 0.9.0. Experiment 6 confirms the negotiated version.

## Experiments

1. **Session in a given workspace, as another user.** The host process runs as `gs-host`; it starts a Claude Code session through `@ahpd/agent-acp` whose agent process runs as a separate Unix user (`gs-agent-1`), in `/var/lib/grindstone/workspaces/<run>`, inside the agent-host container. *Pass:* the agent writes a file there; `id` inside the agent shows the agent user; the agent cannot read the host's token file (mode 0600, owned by `gs-host`).
   - Record the **minimum capabilities** this needs. `compose.yaml` currently drops all capabilities with `no-new-privileges`; switching uid needs `CAP_SETUID` and `CAP_SETGID` in the host process (or a small helper). Measure exactly what is required; SPEC-05 must state it.
2. **Per-session MCP server and token** (Q-1, ADR-16). Each session gets `mcp_url` plus a bearer token naming task, run and capability, passed through the control API's `create_session`. Try, in order: an `@ahpd/sdk` per-session option, if one exists; per-session configuration through `@ahpd/agent-acp`; a minimal patch to the vendored `@ahpd/agent-acp`. *Pass:* two concurrent sessions each call a stub MCP server with only their own token, and a session using the other's token is refused.
3. **Stub kernel MCP server** (Q-6): FastMCP mounted in a FastAPI app, verifying the bearer token on every request (not only at connect). *Pass:* a tool call with a revoked token fails mid-session. Record whether FastMCP 4.1.0 runs on the official MCP SDK 2.3.0, and the mount code.
4. **Subscription credential and its precedence** (ADR-18). Run the session on the operator's subscription token. From the Claude Code documentation current on the day, list every credential source and setting that would outrank it (API-key environment variables, API-key helpers, cloud-provider switches, settings files), and write a start-up self-test that fails if any is present. *Pass:* the self-test fails with each source set in turn and passes with none.
5. **Repository configuration kept out** (ADR-18, ADR-39). Put a hostile `.claude/settings.json` (with a hook), `.mcp.json`, `CLAUDE.md` and a skill directory into the workspace. *Pass:* none of them takes effect; record the exact flags or settings-source option that achieves it. Then materialize one skill read-only into the session's private configuration directory, outside the workspace, and confirm the agent discovers it natively (ADR-39). Decide and record whether `CLAUDE.md` in a repository counts as configuration (excluded) or as project content the context pack may carry.
6. **AHP clients** (Q-2). A browser client attaches to the live session through AHP with a connection token; VS Code attaches as a remote agent host. Record the negotiated AHP version and the VS Code version. *Pass:* both see the transcript live; steering from VS Code is delivered and visible to the host. In a cloud session nothing outside the container can reach the host: run the browser-side check with a headless AHP client inside the container, and attach VS Code through a tunnel (the ahpd project ships `@ahpd/tunnel-devtunnel`) or defer that half to the first session on a machine VS Code can reach; record which was done.
7. **Permission requests.** The agent asks to run a command outside its allow-list. *Pass:* the request reaches the control API as an event; an answer through `answer_permission` is honoured; the same answer sent from the browser AHP client is refused.
8. **Host restart mid-turn.** Kill the host process during a turn. *Pass:* the control plane's view (`list()` after restart) shows the session gone; a new session on the same workspace continues; record exactly what the host reports and what is lost.
9. **Signed events.** The host emits session events HMAC-signed with event IDs and turn numbers; a replayed or forged event is detectable. Measure event latency from the agent to the control plane.

## Record

Versions of `@ahpd/sdk`, `@ahpd/agent-acp`, `@agentclientprotocol/claude-agent-acp`, `@microsoft/agent-host-protocol`, Claude Code, FastMCP, MCP SDK, VS Code; the capability set; the patch, if any, as a diff; session start latency; the credential-precedence list with its source.

## Fallback

If experiments 1, 2 or 6 cannot pass within the box: M1 drives the Claude ACP adapter through a minimal host of our own behind the same control API and events, and live sessions in the browser move to M4 (SPK-1 fallback in the Roadmap). Any change to ADR-15 is a superseding record.

## Report (17 October 2026)

**Every experiment passed. Q-1, Q-2 (for AHP clients) and Q-6 are answered.** No package needs a patch, so the default answer to Q-1, a patched plugin, changes: see "Proposed amendment" below. Four findings shape SPEC-05:
- the host gates actions only when it has a people directory;
- agents can outlive a killed host;
- workspace ownership must let the host enter the workspace;
- the host needs exactly `CAP_SETUID` and `CAP_SETGID`.

The VS Code half of experiment 6 is deferred to a session on a machine VS Code can reach.

How it ran: in a Claude Code cloud session, with live turns on the operator's subscription (`GRINDSTONE_CLAUDE_OAUTH_TOKEN`, passed to the agent only, as `CLAUDE_CODE_OAUTH_TOKEN`).

| Component | Version |
| --- | --- |
| Node | 24.22.0 |
| `@ahpd/sdk` | 0.12.0 |
| `@ahpd/agent-acp` | 0.12.0 |
| `@agentclientprotocol/claude-agent-acp` | 0.93.0 |
| Claude Agent SDK | 0.3.300, which bundles Claude Code 2.1.300 (2.1.302 is the latest on npm) |
| `@agentclientprotocol/sdk` | 1.9.0 |
| `@microsoft/agent-host-protocol` | 1.0.0 |
| FastMCP | 4.1.0 |
| `mcp` | 2.3.0 |
| FastAPI | 0.143.3 |

Spike code and results are in `spk1/` on branch `claude/youthful-franklin-oq4j5j` of `ex1tium/grindstone-testbed` (never merged):
- `src/host.mjs`: the host, with the wrapper backend and the event signer;
- `src/launcher.mjs`: the vendored plugin;
- `src/selftest.mjs`: the credential self-test;
- `src/control.mjs`: the control side's AHP client;
- `mcp/server.py`: the kernel MCP stub;
- `docker/Dockerfile`: experiment 1;
- `results/exp*.json`.

Session start through the host: 1.0 s to an open ACP session; a one-file turn took 5.4 s end to end.

### The shape that emerged (for SPEC-05)

- **Host**: `createHost` from `@ahpd/sdk` with one backend, a ~40-line wrapper around `acpAgent` from `@ahpd/agent-acp`. For each session, the wrapper reads Grindstone's record of the session from the control side's table, keyed by the session UUID; clients name `ahp-session:/<uuid>` and the backend sees `<provider>:/<uuid>`. From that record it:
  - adds the session's kernel MCP server, `{ type: 'http', url, headers: { Authorization: 'Bearer …' } }`, to `start.mcpServers`;
  - creates an `acpAgent` for that session alone, so the agent process gets its own environment and Unix user.
- **Vendored ACP agent plugin**: a ~50-line launcher. It runs the credential self-test, then starts `claude-agent-acp` behind a stdio proxy that merges Grindstone's Claude Code options into the `_meta.claudeCode.options` of every `session/new`, load, resume and fork. The default is `settingSources: []`. `claude-agent-acp` spreads these options over its defaults, which load `user`, `project` and `local` settings.
- **Control side**: an AHP client on the root token. It creates sessions, dispatches `chat/turnStarted`, watches each chat's actions, and answers `chat/toolCallReady` with `chat/toolCallConfirmed`.
- **Environment**: `@ahpd/agent-acp` merges the agent's `env` over the host's own environment. So the host process runs with a minimal environment, and the wrapper hands each agent only `PATH`, `HOME`, `CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_OAUTH_TOKEN` and the launcher's options.

### Results

| # | Result | Evidence |
| --- | --- | --- |
| 1 | pass | In the pinned agent-host base image, with `--cap-drop ALL`, `--cap-add SETUID --cap-add SETGID` and `no-new-privileges`. **Host:** uid 10002 (`gs-host`), `CapEff` `0xc0`, exactly those two capabilities, kept as ambient capabilities through `setpriv`. **Agent:** started by the wrapper through `setpriv --reuid=gs-agent-1 --regid=gs-agent-1 --init-groups --inh-caps=-all --ambient-caps=-all`; all four of its processes (launcher, adapter, two Claude Code processes) ran as uid 10201 with `CapEff` 0. Its own `id` showed `uid=10201(gs-agent-1)`, and the file it wrote in its workspace is owned by 10201. **Boundary:** tested as `gs-agent-1` without the model, `cat` of the host's token file (0600, `gs-host`) and `ls` of `/run/gs-host` both fail with `Permission denied`, as does listing the workspaces root. **Minimum capabilities:** without `SETGID` the switch fails (`setresgid failed: Operation not permitted`); without both it fails at `setresuid`. **Layout that works:** workspaces root `root:gs-workspaces` with mode 2771 (agents traverse, nobody lists), and each run directory owned by its agent user, group `gs-workspaces`, mode 2750. `@ahpd/agent-acp` spawns the agent with the workspace as its working directory, so the host must be able to enter it; mode 0700 for the agent alone fails with `spawn setpriv EACCES`. A first prompt also asked the agent to `cat` the host's token file. The model declined it as exfiltration, and Claude Code fell back from Sonnet 5.5 to Sonnet 5 for the rest of that session. So the boundary was tested directly instead. |
| 2 | pass | Two concurrent sessions, each given the stub kernel server with its own token through the wrapper. Each called `mcp__grindstone__whoami`, and the server attributed each call to the right session (one call by A, two by B). After A's token was revoked mid-session, A's next call was refused with 401 and B's still succeeded. Claude Code found the tools through `ToolSearch`, loading MCP tools on demand. No change to either package (Q-1). |
| 3 | pass | FastMCP 4.1.0 runs on the official MCP SDK 2.3.0 (`fastmcp-slim` requires `mcp>=2.0,<3`). The mount: `mcp_app = mcp.http_app(path="/mcp")`; `app = FastAPI(lifespan=mcp_app.lifespan)`; `app.mount("/kernel", BearerPerRequest(mcp_app))`. A 20-line pure ASGI middleware checks the token against the live table on every HTTP request. A tool reads the caller's identity with `get_http_headers()`. Through one client session: a call with a live token was answered, the next call after revocation was refused with 401, and a forged token could not list the tools (Q-6). |
| 4 | pass | The precedence list and the self-test are below. Each of 36 sources set in turn fails the self-test; with none set, it passes. Set for real, an API key outranks the token, and a base URL reroutes it. |
| 5 | pass | A workspace with a hostile `.claude/settings.json` (`SessionStart` and `PreToolUse` hooks, an `env` block, `enableAllProjectMcpServers`, `permissions.allow`), a `.mcp.json` server, a `CLAUDE.md` and `.claude/skills/evil-skill`. **Claude Code's defaults**: both hooks ran, the `env` value leaked into the shell, `CLAUDE.md` was read, the repository skill was offered, and the `.mcp.json` server was started. **Through the launcher** (`settingSources: []`): none of them took effect. **With `settingSources: ["user"]`** and a private `CLAUDE_CONFIG_DIR` holding one skill (read-only: file 0444, directories 0555): that skill was discovered natively, and still nothing from the repository loaded (ADR-39). Claude Code's own bundled skills (`code-review`, `simplify`, `init` and others) are offered in every case. |
| 6 | pass (headless client); VS Code deferred | A second client, connecting with a viewer token through the host's `identify`, negotiated **AHP 1.0.0**, the same as the control side, with `SUPPORTED_PROTOCOL_VERSIONS` from `@microsoft/agent-host-protocol` 1.0.0. It subscribed to the live session and received every action the control side received, at most 2 ms later (38 actions, none missing). Its follow-up message steered the session: the turn started, the control side saw it, and the work was done. The VS Code half needs a machine VS Code can reach (Q-2's VS Code part). |
| 7 | pass | A permission request reaches the control side as `chat/toolCallReady`, with Claude Code's options (`allow-once`, `allow-with-updates`, `reject`), and as `session/inputNeededSet` on the session. The control side's `chat/toolCallConfirmed` with `selectedOptionId: "allow-once"` was honoured. The viewer's identical answer was refused: the host asked the viewer principal for `chat:answer`, was told no, and nothing ran. **Finding:** `@ahpd/sdk` checks grants on dispatched actions only when the host has a people directory (`options.users`; `host/actions.js`). Without one, the first run accepted the viewer's answer and the file was written. A minimal directory (`{ resource: {}, verify(token) }`) turns the checks on. The grants the viewer was asked for: `config:settings`, `session:state`, `chat:turns`, `chat:answer`, `chat:send`. |
| 8 | pass, with a finding | The host process was killed with SIGKILL during a turn. After restart, the control side sees no sessions (`listSessions` → `[]`, `activeSessions` 0), and subscribing to the old session URI fails with `-32001 No agent for session`: the default `memorySessions()` keeps nothing. A new session on the same workspace carried on and saw the files left behind. **Finding:** the Claude Code process did not die with the host. It was reparented to init and kept working: `done.txt`, the interrupted turn's last step, was written by that orphan after the host was dead, while the interrupted `sleep && echo` never wrote its file. SPEC-05 must make agents die with their host: the host as the container's PID 1, so the container stopping kills the PID namespace, or a parent-death signal set on each agent, or both. |
| 9 | pass | The host wraps the root connection's `notify` and signs every `action` it sends the control side. Each carries an event ID, the chat's turn number, a timestamp, and an HMAC-SHA256 over those plus channel, `serverSeq` and action, under a key only the host and the control plane hold. All 61 actions of a live turn verified. A replayed event (`replayed`), a tampered action (`forged`), one signed with another key (`forged`) and a fresh event ID reusing a sequence number (`out of order`) were all detected. Latency from the agent emitting a tool-call update (timestamped by the launcher) to the verified event at the control side: 2–5 ms, mean 3.3 ms, over 4 tool calls. Production should sign canonical JSON (RFC 8785) rather than relying on key order. |

### Credential precedence (experiment 4, ADR-18)

From the Claude Code documentation read on 17 October 2026 (`code.claude.com/docs/en/authentication`, "Authentication precedence", with the variable names from `/env-vars` and the paths from `/managed-settings`), Claude Code chooses:

1. Cloud provider credentials, when `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX` or `CLAUDE_CODE_USE_FOUNDRY` is set (the variable reference adds `CLAUDE_CODE_USE_ANTHROPIC_AWS` and `CLAUDE_CODE_USE_MANTLE`);
2. `ANTHROPIC_AUTH_TOKEN`;
3. `ANTHROPIC_API_KEY`;
4. `apiKeyHelper` output (a settings key);
5. **`CLAUDE_CODE_OAUTH_TOKEN`**, the long-lived token from `claude setup-token`, which Grindstone uses;
6. Anthropic profile and federation credentials (`ANTHROPIC_PROFILE`, `ANTHROPIC_FEDERATION_RULE_ID` with `ANTHROPIC_ORGANIZATION_ID`, or an active profile);
7. subscription OAuth from `/login`.

A signed-in Claude apps gateway session sits above the whole list, and managed settings can force it (`forceLoginMethod: "gateway"`, `forceLoginGatewayUrl`). Managed settings (`/etc/claude-code/managed-settings.json`, `managed-settings.d/`, `managed-mcp.json` on Linux) **apply to Agent SDK sessions even when `settingSources` excludes every source**, and a settings file's `env` block can set any of the variables above. Bare mode does not read `CLAUDE_CODE_OAUTH_TOKEN`, so Grindstone must never pass `--bare`. The adapter offers no ACP `authMethods`, so the environment variable is the only sign-in.

The start-up self-test (`spk1/src/selftest.mjs`) refuses to start the session if any of the following holds:
- `CLAUDE_CODE_OAUTH_TOKEN` is missing;
- any of 27 provider, credential, route or gateway variables is set: tiers 1–3, the other providers' keys and base URLs, `CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST`, the `CLAUDE_CODE_SKIP_*_AUTH` switches, profiles and federation, and `CLAUDE_CODE_OAUTH_REFRESH_TOKEN`;
- any managed-settings file or directory exists;
- `CLAUDE_CONFIG_DIR` is unset;
- the private configuration directory holds a stored login, or a `settings.json` that sets `apiKeyHelper`, `env`, or a `forceLogin*` or `allowedProviders` key.

### Decisions this records, and what SPEC-05 must take

- **`CLAUDE.md` in a repository is configuration and is excluded.** `settingSources: []` keeps it out natively; Claude Code also has `CLAUDE_CODE_DISABLE_CLAUDE_MDS`. If a project wants its `CLAUDE.md` in front of agents, the context pack carries it as a pinned item like any other project content, recorded on the run, so the operator sees it and it can be reviewed.
- **Bundled skills.** Claude Code's bundled skills are always offered. Whether a capability may use them (most are harmless; `init` writes a `CLAUDE.md`) is a question for SPEC-05's tool policy, not for discovery.
- **Grants need a people directory.** The host must be configured with a `users` directory: viewers get every grant they need to watch and steer, never `chat:answer`, so permission answers come only from the control side (ADR-15).
- **Agents die with their host** (experiment 8): PID 1 or a parent-death signal, plus a check at start-up that no agent process from an earlier host is left.
- **Workspace layout and capabilities** as in experiment 1: the host holds `CAP_SETUID` and `CAP_SETGID` only; run directories are `<agent user>:gs-workspaces` with mode 2750.
- **The agent environment is built, never inherited**, because `@ahpd/agent-acp` merges over the host's own. The TLS CA of an intercepting egress, if any, is passed to the agent explicitly as `NODE_EXTRA_CA_CERTS`; in this cloud session, a container's traffic to the Anthropic API is TLS-inspected.
- **Session records are kept outside the host.** The default store forgets everything on restart, which is what ADR-15 allows ("correctness never depends on a session surviving a restart"). Claude Code still keeps its own transcript in the session's `CLAUDE_CONFIG_DIR`, which a resume could use; not tested.
- **The model may fall back during a session.** A refusal moved one session from Sonnet 5.5 to Sonnet 5 for the rest of the session. Runs should record the model of each turn from the events, not assume the one configured.

### Proposed amendment to ADR-15: accepted as ADR-42 (foundation v4.5)

ADR-15 says the host uses "a vendored, patched ACP agent plugin". The spike shows no patch is needed: `@ahpd/sdk` and `@ahpd/agent-acp` are used unmodified. The two Grindstone pieces are (1) a backend wrapper that adds the per-session kernel MCP server and token and builds each agent's environment and user, and (2) the vendored plugin as a launcher in front of the unmodified `claude-agent-acp` that enforces Grindstone's Claude Code options and runs the credential self-test. The proposal is to supersede the words "vendored, patched ACP agent plugin" with "a vendored launcher in front of the unmodified ACP agent, and a backend wrapper", and to change Q-1's answer to match. That needs a decision record (append-only) when SPEC-05 is written.
