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
| pyyaml | 6.0.3 | 2025-09-25 | Factory manifests and capability files, safe loader only (SPEC-03, DEC-0302); pinned by TKT-0302 |
| dbos | 3.3.0 | 2026-10-15 | Workflows and datasource transactions (ADR-03, SPEC-02); pinned by TKT-0201, re-checked on the PyPI JSON API on 24 October 2026 |
| jsonschema | 4.26.0 | 2026-01-07 | Validates capability report schemas at load (SPEC-03, REQ-0306) and, from SPEC-06, reports against them; no specification named a validator, so TKT-0302 added the latest release |
| packaging | 26.3 | 2026-08-04 | PEP 440 SDK ranges in factory manifests (SPEC-03, DEC-0303); pinned by TKT-0302 |
| rfc8785 | 0.1.4 | 2024-09-27 | RFC 8785 canonical JSON for semantic hashes (SPEC-01, DEC-0103); pinned by TKT-0103, still the latest on the PyPI JSON API on 24 October 2026 |
| sqlalchemy | 2.1.6 | 2026-10-21 | SQLAlchemy Core over psycopg 3, shared with DBOS's datasource (SPEC-02, DEC-0201). DEC-0201 named 2.1.5, the latest when SPEC-02 was written; 2.1.6 is the latest compatible release on 24 October 2026 (ADR-46) |
| pytest | 9.1.1 | 2026-06-19 | Tests |
| hypothesis | 6.170.1 | 2026-10-16 | Property tests (from M1) |
| httpx2 | 2.13.1 | 2026-09-23 | Starlette's test client; `httpx` with the test client is deprecated in Starlette 1.x |
| import-linter | 2.15 | 2026-09-04 | FF-01 |
| ruff | 0.17.1 | 2026-10-15 | Lint and format |
| argon2-cffi | 25.1.0 | 2025-06-03 | Argon2id hash of the operator password, written by `make secrets` through `scripts/hash_password.py` (SPEC-05, REQ-0513) and verified by SPEC-10; a development dependency until SPEC-10 adds it to the control plane. Pinned by TKT-0501, still the latest on the PyPI JSON API on 25 October 2026; it brings `argon2-cffi-bindings` 26.1.0 (abi3 wheels), `cffi` 2.1.1 and `pycparser` 3.12, locked in `uv.lock` |

## Node packages

| Package | Pinned | Released | Used for |
| --- | --- | --- | --- |
| typescript | 7.0.2 | 2026-07-08 | Type checking; the native compiler. **Check at SPEC-10:** that `svelte-check` supports TypeScript 7 before the web UI is scaffolded |
| @biomejs/biome | 2.5.15 | 2026-09-30 | Lint and format |
| pyright | 1.1.414 | 2026-09-09 | Python strict type checking, installed from npm so no runtime download happens |
| json-schema-to-typescript | 16.0.0 | 2026-08-28 | FF-02 TypeScript generation |
| @types/node | 24.19.2 | 2026-10-09 | Matches the Node 24 runtime |
| canonicalize | 5.1.0 | 2026-09-18 | RFC 8785 canonical JSON for semantic hashes in `@grindstone/contracts` (SPEC-01, DEC-0103); pinned by TKT-0104, still the latest on the npm registry on 25 October 2026 |

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
| dbos | 3.3.0 | 2026-10-15 | SPK-2 | Declares Python up to 3.14. Pinned since TKT-0201 (above) |
| fastmcp | 4.1.0 | 2026-10-08 | SPK-1 (Q-6) | Kernel MCP surface |
| mcp | 2.3.0 | 2026-10-02 | SPK-1 (Q-6) | Official MCP Python SDK, the fallback |

The Claude credential-precedence list required by M0-03 is recorded by SPK-1 from the Claude Code documentation current at the time of the spike.

## Resolved for the M1 specifications, not yet pinned

Checked on 17 October 2026 against the PyPI JSON API and the npm registry while SPEC-02 to SPEC-10 were written. As above, each is pinned only when its code lands; the specification named decides it.

| Package | Latest | Released | Specification | Observation |
| --- | --- | --- | --- | --- |
| sqlalchemy | 2.1.5 | 2026-10-16 | SPEC-02 | Already in the lockfile through DBOS; pinned directly for DBOS datasource transactions. Pinned at 2.1.6 since TKT-0201 (above) |
| pyyaml | 6.0.3 | 2025-09-25 | SPEC-03 | Safe loader only; CPython 3.14 wheels. Pinned since TKT-0302 (above) |
| packaging | 26.3 | 2026-08-04 | SPEC-03 | SDK range checks; already in the lockfile. Pinned since TKT-0302 (above) |
| argon2-cffi | 25.1.0 | 2025-06-03 | SPEC-05 (written by `make secrets`), SPEC-10 (verified) | Operator password hash; `argon2-cffi-bindings` 26.1.0 ships abi3 wheels. Pinned since TKT-0501 (above) |
| pyjwt | 2.15.1 | 2026-09-28 | SPEC-09 | The GitHub App's RS256 JWT, as SPK-4 used it |
| cryptography | 50.0.2 | 2026-09-30 | SPEC-09 | RS256 for PyJWT |
| fastmcp, mcp | 4.1.0, 2.3.0 | 2026-10-08, 2026-10-02 | SPEC-07 | As SPK-1 ran them |
| `@ahpd/sdk`, `@ahpd/agent-acp` | 0.12.0 | 2026-10-16 | SPEC-06 | Unchanged since SPK-1 |
| `@agentclientprotocol/claude-agent-acp` | 0.93.0 | 2026-10-16 | SPEC-05, SPEC-06 | Unchanged since SPK-1 |
| `@agentclientprotocol/sdk` | 1.9.0 | 2026-10-16 | SPEC-06 | The scripted preset |
| `@modelcontextprotocol/sdk` | 1.32.1 | 2026-10-05 | SPEC-06 | The scripted preset's MCP client |
| `@sveltejs/kit` | 3.1.0 | 2026-10-14 | SPEC-10 | Peer range `typescript ^6.0.0` |
| svelte | 5.57.2 | 2026-10-06 | SPEC-10 | — |
| `@sveltejs/adapter-static` | 4.0.0 | 2026-10-01 | SPEC-10 | — |
| `@sveltejs/vite-plugin-svelte` | 7.3.1 | 2026-09-23 | SPEC-10 | — |
| vite | 8.3.4 | 2026-10-08 | SPEC-10 | — |
| svelte-check | 4.7.7 | 2026-10-16 | SPEC-10 | Peer range `typescript ^5.0.0 \|\| ^6.0.0`: the check this file asked SPEC-10 to make. **TypeScript 7 is not supported**, so `web/` pins TypeScript 6.0.3 (2026-04-16) and the rest of the repository stays on 7.0.2 (SPEC-10, DEC-1003). An exception under ADR-46: it ends when SvelteKit and svelte-check accept TypeScript 7, re-checked at every upgrade |
| `@playwright/test` | 1.64.1 | 2026-10-14 | SPEC-10 | End-to-end tests of the web shell |
| openapi-typescript | 7.13.0 | 2026-02-11 | SPEC-10 | Not used: peer range TypeScript 5 (SPEC-10, DEC-1002) |

## Environment notes

- Docker Hub rate-limits anonymous pulls per IP. Shared CI and cloud environments hit it; on the operator's hosts use authenticated pulls or a pull-through mirror. Digests are identical through a mirror, so pins hold.
- Image builds behind a TLS-intercepting proxy pass the proxy's CA as the build secret `build_ca` and the proxy as the standard `HTTPS_PROXY` build argument (`docker/grindstone.Dockerfile`).
