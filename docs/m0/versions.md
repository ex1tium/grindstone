# Resolved versions (M0-03)

Resolved on 17 October 2026 from the primary sources named below: the PyPI JSON API, the npm registry, the Node.js release index, Docker Hub and GHCR manifests, and the GitHub tags of each action. Every value is pinned exactly in the repository (FF-04); this file records why each was chosen. Dependabot proposes upgrades, which are deliberate pull requests that must pass CI (ADR-01).

## Runtimes and images

| Component | Pinned | Released | Why this one |
| --- | --- | --- | --- |
| Python | 3.14.8 | — | Latest stable that every control-plane dependency declares support for. Python 3.15.0 is out, but DBOS 3.3.0, FastAPI 0.143.3, uvicorn 0.54.0 and the MCP SDK 2.3.0 do not yet declare 3.15. Revisit when they do |
| Node.js | 24.22.0 (Active LTS) | 2026-10-14 | Node 26 is Current and enters LTS at the end of October 2026; move to it then. **Note:** Node 25 and later no longer bundle Corepack, which installs our hash-pinned pnpm; the upgrade must install Corepack separately or switch CI to `pnpm/action-setup` |
| pnpm | 12.14.0 (sha512-pinned in `packageManager`) | 2026-10-15 | Latest; installed by Corepack, which verifies the hash |
| uv | 0.13.1 | 2026-10-14 | Latest; also the build backend (`uv_build`) |
| `python` image | `3.14.8-slim-trixie@sha256:a2b82f3c…3729170` | — | Official image, Debian 13 slim |
| `node` image | `24.22.0-trixie-slim@sha256:7f486cab…bec315` | — | Official image, Debian 13 slim |
| `postgres` image | `18.6-trixie@sha256:74935e72…dcfc4336` | — | PostgreSQL 18 is the latest stable major; 19 is at release candidate |
| `uv` image | `ghcr.io/astral-sh/uv:0.13.1@sha256:4a1f3666…ada336` | — | Copies the uv binary into the build stage |

## Python packages

| Package | Pinned | Released | Used for |
| --- | --- | --- | --- |
| pydantic | 2.14.1 | 2026-10-11 | Contracts (ADR-05) |
| fastapi | 0.143.3 | 2026-10-16 | REST API and health |
| uvicorn | 0.54.0 | 2026-09-25 | ASGI server |
| psycopg[binary] | 3.3.6 | 2026-09-18 | PostgreSQL driver |
| pytest | 9.1.1 | 2026-06-19 | Tests |
| hypothesis | 6.170.1 | 2026-10-16 | Property tests (from M1) |
| httpx2 | 2.13.1 | 2026-09-23 | Starlette's test client; `httpx` with the test client is deprecated in Starlette 1.x |
| import-linter | 2.15 | 2026-09-04 | FF-01 |
| ruff | 0.17.1 | 2026-10-15 | Lint and format |

## Node packages

| Package | Pinned | Released | Used for |
| --- | --- | --- | --- |
| typescript | 7.0.2 | 2026-07-08 | Type checking; the native compiler. **Check at SPEC-10:** that `svelte-check` supports TypeScript 7 before the web UI is scaffolded |
| @biomejs/biome | 2.5.15 | 2026-09-30 | Lint and format |
| pyright | 1.1.414 | 2026-09-09 | Python strict type checking, installed from npm so no runtime download happens |
| json-schema-to-typescript | 16.0.0 | 2026-08-28 | FF-02 TypeScript generation |
| @types/node | 24.19.2 | 2026-10-09 | Matches the Node 24 runtime |

## GitHub Actions

| Action | Tag | Commit |
| --- | --- | --- |
| actions/checkout | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| astral-sh/setup-uv | v10.3.0 | `1c37ad07a6a961277cf70c0d37d6f313000f5884` |
| actions/setup-node | v7.1.0 | `949feb2413d6458794dcd2491c4babbbce0c15c1` |

## Resolved for the spikes, not yet pinned

These are what the spikes start from. Each is pinned in a manifest only when the code that uses it lands, so nothing unused sits in the lockfiles.

| Package | Latest | Released | Spike | Observation |
| --- | --- | --- | --- | --- |
| `@ahpd/sdk` | 0.12.0 | 2026-10-16 | SPK-1 | MIT, `github.com/softov/ahpd`. Pre-1.0, with four minor releases in the twelve days since 0.9.0 (4 October): the API will move. This is the risk the foundation names ("the agent-host ecosystem is young"); SPK-1 decides whether to build on it or take the minimal-host fallback |
| `@agentclientprotocol/sdk` | 1.9.0 | 2026-10-16 | SPK-1 | ACP client library, maintained by the ACP project |
| `@agentclientprotocol/claude-agent-acp` | 0.93.0 | 2026-10-16 | SPK-1 | The Claude ACP adapter the foundation calls "the vendored ACP agent plugin"; it superseded `@zed-industries/claude-code-acp`, last released March 2026 |
| `@modelcontextprotocol/sdk` | 1.32.1 | 2026-10-05 | SPK-1 | Stub MCP clients in tests |
| dbos | 3.3.0 | 2026-10-15 | SPK-2 | Declares Python up to 3.14 |
| fastmcp | 4.1.0 | 2026-10-08 | SPK-1 (Q-6) | Kernel MCP surface |
| mcp | 2.3.0 | 2026-10-02 | SPK-1 (Q-6) | Official MCP Python SDK, the fallback |

The Claude credential-precedence list required by M0-03 is recorded by SPK-1 from the Claude Code documentation current at the time of the spike.

## Environment notes

- Docker Hub rate-limits anonymous pulls per IP. Shared CI and cloud environments hit it; on the operator's hosts use authenticated pulls or a pull-through mirror. Digests are identical through a mirror, so pins hold.
- Image builds behind a TLS-intercepting proxy pass the proxy's CA as the build secret `build_ca` and the proxy as the standard `HTTPS_PROXY` build argument (`docker/grindstone.Dockerfile`).
