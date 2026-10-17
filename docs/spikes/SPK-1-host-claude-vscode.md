# SPK-1 — Host, Claude and VS Code

Status: in progress · Box: 2 days · Settles: Q-1, Q-2, Q-6; the Claude credential-precedence list (M0-03); the assumption that an AHP host on `@ahpd/sdk` can run Claude Code sessions with a per-session MCP server (Architecture, "Constraints, assumptions and capacity")

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

## Report (partial, 17 October 2026)

Run in a Claude Code cloud session on Node 24.22.0, with `@ahpd/sdk` 0.12.0, `@ahpd/agent-acp` 0.12.0, `@agentclientprotocol/claude-agent-acp` 0.93.0 (Claude Agent SDK 0.3.300), `@agentclientprotocol/sdk` 1.9.0 and `@microsoft/agent-host-protocol` 1.0.0; Claude Code 2.1.302 is current on npm. The spike code is in `spk1/` on branch `claude/youthful-franklin-oq4j5j` of `ex1tium/grindstone-testbed` (never merged). It is paused because the operator's subscription reached its session limit at 16:28 UTC (`You've hit your session limit`): every live call draws on that subscription.

### Claude Code runs here on the subscription token

`claude-agent-acp` started by a raw ACP client over stdio, with a clean environment (a fresh `HOME`, a private `CLAUDE_CONFIG_DIR`, and only `CLAUDE_CODE_OAUTH_TOKEN` set from `GRINDSTONE_CLAUDE_OAUTH_TOKEN`): `initialize` → `session/new` in 1.0 s; a turn that wrote a file in the workspace ended `end_turn` after 2.3 s. The adapter offers no ACP `authMethods`, so the environment variable is the only sign-in.

### What the packages allow (read from the 0.12.0 and 0.93.0 sources)

- **Per-session MCP (Q-1).** `@ahpd/sdk` gives each session `Start.mcpServers`: the host-wide `mcpServers` merged with what the session's client plugins add. No option takes a server per session from the control side. `@ahpd/agent-acp` passes `Start.mcpServers` to ACP's `session/new`, including HTTP servers with `headers`, which is where a bearer token goes. So the per-session server and token need no patch: Grindstone's backend can be a small `Agent` wrapper that, in `create(start)`, adds `{ grindstone: { type: 'http', url, headers: { Authorization: 'Bearer …' } } }` to `start.mcpServers` before handing the session to `acpAgent(...)`. The token comes from the control API's own table, keyed by the session URI, so it never sits in session configuration that AHP clients can read. To be confirmed in experiment 2.
- **Claude Code options per session.** `claude-agent-acp` reads `_meta.claudeCode.options` on `session/new` (and load, resume and fork) and spreads it over its defaults, which include `settingSources: ["user", "project", "local"]`. So a client can set `settingSources`, `env`, `tools`, `mcpServers` and the like per session. `@ahpd/agent-acp` sends no `_meta`. The vendored ACP agent plugin of ADR-15 is therefore a **launcher**: `claude-agent-acp` behind a stdio proxy that merges Grindstone's options into every `session/new`, load, resume and fork (`spk1/src/launcher.mjs`, 30 lines), and runs the credential self-test before starting. No package is patched.
- **FastAPI-side note for SPEC-05:** `@ahpd/agent-acp` spawns one ACP process per host session, and its `env` option is per agent registration; the wrapper creates one registration per session, so each session's process can get its own environment.

### Experiment 4 — Subscription credential and its precedence: pass

From the Claude Code documentation read on 17 October 2026 (`code.claude.com/docs/en/authentication`, "Authentication precedence", with the variable names from `/env-vars` and the paths from `/managed-settings`), Claude Code chooses:

1. Cloud provider credentials when `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX` or `CLAUDE_CODE_USE_FOUNDRY` is set (the variable reference adds `CLAUDE_CODE_USE_ANTHROPIC_AWS` and `CLAUDE_CODE_USE_MANTLE`);
2. `ANTHROPIC_AUTH_TOKEN`;
3. `ANTHROPIC_API_KEY`;
4. `apiKeyHelper` output (a settings key);
5. **`CLAUDE_CODE_OAUTH_TOKEN`**, the long-lived token from `claude setup-token`, which Grindstone uses;
6. Anthropic profile and federation credentials (`ANTHROPIC_PROFILE`, `ANTHROPIC_FEDERATION_RULE_ID` with `ANTHROPIC_ORGANIZATION_ID`, or an active profile);
7. subscription OAuth from `/login`.

A signed-in Claude apps gateway session sits above the whole list, and managed settings can force it (`forceLoginMethod: "gateway"`, `forceLoginGatewayUrl`). Managed settings (`/etc/claude-code/managed-settings.json`, `managed-settings.d/`, `managed-mcp.json` on Linux) **apply to Agent SDK sessions even when `settingSources` excludes every source**, and a settings file's `env` block can set any of the variables above. Bare mode does not read `CLAUDE_CODE_OAUTH_TOKEN`, so Grindstone must never pass `--bare`.

The start-up self-test (`spk1/src/selftest.mjs`) refuses to start the session if any of the following holds:
- `CLAUDE_CODE_OAUTH_TOKEN` is missing;
- any of 27 provider, credential, route or gateway variables is set: tiers 1–3, the other providers' keys and base URLs, `CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST`, the `CLAUDE_CODE_SKIP_*_AUTH` switches, profiles and federation, and `CLAUDE_CODE_OAUTH_REFRESH_TOKEN`;
- any managed-settings file or directory exists;
- `CLAUDE_CONFIG_DIR` is unset;
- the private configuration directory holds a stored login, or a `settings.json` that sets `apiKeyHelper`, `env`, or a `forceLogin*` or `allowedProviders` key.

**Result:** with each of 36 sources set in turn, the self-test fails; with none, it passes. Two of the sources, set for real alongside the token, change what Claude Code does, which confirms the precedence: a bogus `ANTHROPIC_API_KEY` makes the session fail with `Authentication required` (the key outranks the token), and an unreachable `ANTHROPIC_BASE_URL` reroutes it until it times out. With neither, the same call answered `OK` (`spk1/results/exp4.json`).

### Still to run

Experiment 5 (written, `spk1/src/exp5.mjs`; interrupted by the limit), then 2, 3, 1, 6, 7, 8 and 9. Experiments 3 and 9 and the Unix-user half of 1 need no model calls; the rest each need a few short turns.
