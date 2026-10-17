# SPK-3 — Codex and pi

Status: deferred until the operator adds a second provider (ADR-41) · Box: 1 day · Settles: Q-3, Q-4, Q-5 (Codex part)

The plan below is kept for when it runs.

## Why

Codex is the second agent (ADR-18, M3): it proves the agent abstraction and gives the auditor and code reviewer a different model family from the author. pi is deferred to R2; its part of this spike is optional and runs only if time remains in the box (Q-5).

## Setup

`@openai/codex` and `@agentclientprotocol/codex-acp` (latest on the day; `@zed-industries/codex-acp` is the older name) behind the SPK-1 host, or behind a plain ACP client if SPK-1 is not finished.

## Experiments

1. **Subscription login, headless** (Q-3). In the agent-host container, with no browser: log Codex in to the operator's ChatGPT subscription with a device-code or token flow. *Pass:* a session runs a turn on the subscription; record how the credential is stored and refreshed, and whether it survives a container restart. If it cannot work headless, use the API key and record why.
2. **API key fallback.** Same session on an API key, configured with no code change. *Pass:* switching between 1 and 2 is configuration only.
3. **Sandbox modes** (Q-4). Run read-only and workspace-write through Codex's own configuration file, supplied per session by the capability. *Pass:* in read-only, a write to the workspace fails; in workspace-write, writes outside the workspace fail.
4. **HTTP MCP with a per-task bearer token.** *Pass:* Codex calls the stub kernel MCP server from SPK-1 with only its own token.
5. **Skills** (Q-5, ADR-39). Where Codex discovers skills natively; materialize one read-only in a session configuration directory outside the workspace. *Pass:* Codex uses it, and ignores a skill planted in the workspace.
6. *(Optional)* pi through its ACP adapter: per-session environment and kernel MCP with a per-task token.

## Record

Codex CLI and adapter versions; the login flow and where its credential lives; the configuration file for each sandbox mode; the skill directory.

## Fallback

API key for Codex (Q-3); `load_skill` inline returns already work for any agent (ADR-39).
