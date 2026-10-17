# SPK-1 — Host, Claude and VS Code

Status: planned · Box: 2 days · Settles: Q-1, Q-2, Q-6; the Claude credential-precedence list (M0-03); the assumption that an AHP host on `@ahpd/sdk` can run Claude Code sessions with a per-session MCP server (Architecture, "Constraints, assumptions and capacity")

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
6. **AHP clients** (Q-2). A browser client attaches to the live session through AHP with a connection token; VS Code attaches as a remote agent host. Record the negotiated AHP version and the VS Code version. *Pass:* both see the transcript live; steering from VS Code is delivered and visible to the host.
7. **Permission requests.** The agent asks to run a command outside its allow-list. *Pass:* the request reaches the control API as an event; an answer through `answer_permission` is honoured; the same answer sent from the browser AHP client is refused.
8. **Host restart mid-turn.** Kill the host process during a turn. *Pass:* the control plane's view (`list()` after restart) shows the session gone; a new session on the same workspace continues; record exactly what the host reports and what is lost.
9. **Signed events.** The host emits session events HMAC-signed with event IDs and turn numbers; a replayed or forged event is detectable. Measure event latency from the agent to the control plane.

## Record

Versions of `@ahpd/sdk`, `@ahpd/agent-acp`, `@agentclientprotocol/claude-agent-acp`, `@microsoft/agent-host-protocol`, Claude Code, FastMCP, MCP SDK, VS Code; the capability set; the patch, if any, as a diff; session start latency; the credential-precedence list with its source.

## Fallback

If experiments 1, 2 or 6 cannot pass within the box: M1 drives the Claude ACP adapter through a minimal host of our own behind the same control API and events, and live sessions in the browser move to M4 (SPK-1 fallback in the Roadmap). Any change to ADR-15 is a superseding record.
