# SPEC-10 — Operator surface, first cut
Status: accepted (by the operator, 19 October 2026, after the reviews in `docs/specs/reviews/`) · Milestone: M1
Kind: kernel · Owns:
- `grindstone.surface` (REST and events): the REST API under `/api/v1` and its OpenAPI document; the per-project and instance event streams; operator login and sessions; idempotency on client keys; the generated TypeScript REST client.
- `web/`: the web shell.

Compact walking-skeleton specification (Planning playbook). Review: by a session that did not write it, then the operator.

## 1. Purpose

The operator decides; everything else in M1 is machinery. This specification gives the operator one authenticated way in, used by the browser and by any later client alike (ADR-06):
- create a project from its configuration;
- import a ticket;
- answer typed decisions on cards with their recommendation in front of them (I-11, ADR-28);
- start a command after seeing its plan;
- follow tasks, runs, evidence and deliveries live.

The UI holds no domain logic: every card is rendered from the decision's payload and kind, and every answer goes through the same decision service.

## 2. Scope

In scope:
- **The REST API, M1 endpoints:**
  - session;
  - projects and their configuration;
  - imports;
  - items, revisions and ChangeSets (read);
  - decisions (list, read, answer);
  - templates and their plan preview;
  - commands;
  - tasks, runs, transcripts, evidence and deliveries (read);
  - asking again for a held delivery's decision.
- **Its machinery:** error mapping, idempotency, and the OpenAPI document with drift and compatibility checks.
- **Event streams:** Server-Sent Events per project and for the instance, resumable with `Last-Event-ID`.
- **Login:** a local password checked against an Argon2id hash, server-side sessions, cookie and CSRF rules, and a login rate limit.
- **The web shell:** login, projects, decision queue and cards, import, commands, tasks and a task page, with live updates.
- **The generated TypeScript REST client.**

Out of scope:
- **Other clients.** Per-client tokens for VS Code and the operator plugin: SPEC-22 and SPEC-26.
- **Other views.** Item pages with graphs, revision diffs across artifacts, and the operations view: SPEC-11, SPEC-22 and SPEC-27.
- **Live sessions.** Viewing, steering and AHP attach in the browser: SPEC-22 (M4).
- **Decisions at scale.** Batched decision cards: SPEC-15 (M3).
- **Exposure.** Beyond loopback, through a TLS proxy: an operator choice documented in SPEC-27's runbook; `[surface].cookie_secure` supports it.

## 3. Foundation links

Implements:
- **ADR-06.** A static SvelteKit UI with Svelte 5, served by the control plane behind operator login, using the generated REST client and Server-Sent Events; one public API with no private endpoints; no domain logic in pages.
- **ADR-28.** Decisions shown identically to every client, answered only through the decision service, with the answer recording who, where and when.
- **I-11.** Every point that needs the operator reaches them as a typed decision with its recommendation on the card.
- **B4** (Threat model). Before authentication, nothing but the login endpoint and health answer. After it, every request is the operator's.
- **Observability.** Every state change reaches the browser as one event with a per-project sequence number, and a reconnect neither misses nor double-counts one. The targets are a decision visible within 1 s of being raised, and an event within 1 s of its state change.

Delivers:
- **M1-01**, the operator's side: "imported from a file as a ChangeSet approved on a decision card"; "after a `delivery` decision" → AC-1003-1, AC-1004-1, AC-1012-1. SPEC-04 delivers the import and apply, and SPEC-09 the live run.
- **M1-08**, the operator's side of running Grindstone's own ticket on the stable instance → AC-1012-1, as part of SPEC-09's live run.

Depends on:
- **SPEC-01:** contracts and the error envelope.
- **SPEC-02:** the unit of work.
- **SPEC-03:** projects and configuration, registries, `events_after`.
- **SPEC-04:** items, ChangeSets and decisions.
- **SPEC-05:** the operator listener, `session_key`, `operator_password_hash` with its Argon2id parameters, and the `argon2-cffi` pin.
- **SPEC-06:** templates, tasks, runs and transcripts.
- **SPEC-08:** evidence summaries, freshness and deliveries.

Scenarios: K1 step 7 (the operator approves the `approval` decision). The operator's part of S1 (approve the import, start the command, answer `delivery`) is exercised by SPEC-09's live run through this surface.

## 4. Requirements

REQ-1001: Every route except `POST /api/v1/session` and the health endpoints requires a valid operator session, and every request that changes state also requires the header `X-Grindstone-CSRF: 1`; the API sends no CORS headers.
REQ-1002: Login checks the password against the Argon2id hash in the `operator_password_hash` secret, creates a server-side session whose identifier is stored only as an HMAC under `session_key`, and sets an `HttpOnly`, `SameSite=Strict` cookie that expires after 12 hours idle or 7 days; more than five failures a minute are refused with 429 until the minute passes.
REQ-1003: `POST /api/v1/projects/{p}/imports` accepts an item bundle and returns the ChangeSet and its `approval` decision, or every item's errors.
REQ-1004: The decision endpoints list open decisions with their kind, flags, recommendation and payload, and accept an answer with the context hash the client saw; the answer records the channel (`ui` when the request carries `X-Grindstone-Client: web`, which the generated client sends from the web shell, otherwise `api`) and the operator. The header is the operator's own claim, which is acceptable because every request is the operator's.
REQ-1005: `GET /api/v1/projects/{p}/templates/{t}/plan` shows a command's steps, needs, matched capabilities and checks for given arguments before it runs, and `POST /api/v1/projects/{p}/commands` starts it.
REQ-1006: The task endpoints return a task with its state, runs and their manifests, turns, check results with freshness and the stale reasons named, and its delivery with mode and verification state; a run's transcript is served from its blob.
REQ-1007: Every command endpoint is idempotent on the `Idempotency-Key` header: the same key with the same body returns the original response, and with a different body is refused with `idempotency_key_reused`.
REQ-1008: Every error response is an `ErrorEnvelope` with an HTTP status fixed by its class.
REQ-1009: `GET /api/v1/projects/{p}/events` streams the project's events as Server-Sent Events with the sequence number as the event ID; a client resuming with `Last-Event-ID` receives every later event exactly once, in order.
REQ-1010: The OpenAPI document is generated from the routes and contracts, committed, and checked for drift; an incompatible change to `/api/v1` fails CI.
REQ-1011: The web shell is a static build served by the control plane; its pages call only the generated client, render decision cards from the decision's kind and payload, and contain no rule that decides what a decision means.
REQ-1012: In the web shell, the operator can log in, create a project from its configuration, import a bundle, approve its ChangeSet on its card with verdicts for every reached item, preview and start a command, answer a `delivery` decision, and see each state change within 1 s without reloading.

## 5. Design

**Routes** (FastAPI on the operator listener, SPEC-05; contracts in `grindstone.contracts.api`, schema version 1):

| Method and path | Does |
| --- | --- |
| `POST`, `GET`, `DELETE /api/v1/session` | Log in, read the session, log out |
| `GET /api/v1/projects`, `POST /api/v1/projects` | List; create with a slug and a TOML configuration |
| `GET /api/v1/projects/{p}`, `PUT /api/v1/projects/{p}/config` | Project with its configuration version, hash, validity and factory status; a new configuration version |
| `POST /api/v1/projects/{p}/imports` | Item bundle (`application/yaml`) → ChangeSet and decision |
| `GET /api/v1/projects/{p}/items/{id}` and `…/revisions/{rev}` | Current or given revision, rendered and typed, with lifecycle state |
| `GET /api/v1/projects/{p}/changesets/{id}` | Proposed revisions with field diffs against their bases, reached items |
| `GET /api/v1/projects/{p}/decisions?state=open`, `GET …/decisions/{d}` | Decisions with payload and recommendation |
| `POST /api/v1/projects/{p}/decisions/{d}/answer` | `{answer, context_hash}` |
| `GET /api/v1/projects/{p}/templates`, `GET …/templates/{t}/plan?args=…` | Commands available; a plan preview |
| `POST /api/v1/projects/{p}/commands` | `{template, args}` → template run |
| `GET /api/v1/projects/{p}/tasks`, `GET …/tasks/{t}`, `GET …/runs/{r}/transcript` | Task views; transcript blob |
| `GET /api/v1/projects/{p}/deliveries/{id}`, `POST …/deliveries/{id}/decision` | Delivery; ask again for a held delivery's decision (SPEC-08) |
| `GET /api/v1/projects/{p}/events`, `GET /api/v1/events` | Project and instance event streams |

The routes call module services only (Components, "Module map": `surface` may use every module's public interface), never tables.

**Errors (REQ-1008).**

| Class | Status |
| --- | --- |
| Validation | 422 |
| Rule | 409 |
| Authority | 403, or 409 for `context_changed`, `decision_superseded` and `decision_closed` |
| Limit | 409, with `retryable` from the envelope; only the login rate limit is 429, because only it means "too many requests" |
| Transient | 503, with `Retry-After` |
| Internal | 500, with no detail |

An unauthenticated request gets 401 with code `login_required`.

**Login (REQ-1002).**
- **Hashing:** verified with `argon2-cffi`, pinned by SPEC-05, which owns the Argon2id parameters and writes the hash with `make secrets`. Verification reads the parameters from the hash itself. The hash is read once at start.
- **Sessions:** in `surface.sessions (id_hmac, created_at, last_seen, expires_at, user_agent)`. A 256-bit random ID goes in the cookie `gs_session`.
- **Cookie:** `Secure` when `[surface].cookie_secure` is true, for operators behind a TLS proxy. Browsers treat `http://127.0.0.1` as a secure context, so loopback works without it.
- **Rate limit:** failures are counted in memory per minute. One operator needs no per-address table.

**Idempotency (REQ-1007).** `surface.idempotency (key, route, body_sha256, response, status, created_at)`, kept for 24 hours.
1. A request with a known key and the same body returns the stored response.
2. A request with a new key passes the key to its service as `client_key`. Decision answers, ChangeDrafts and template runs store it uniquely (SPEC-04, SPEC-06), so a crash between the effect and storing the response still returns the original result on retry.
3. The stored response is written after the service returns.

**Events (REQ-1009).**
- Reads `platform.events_after(project, seq)` (SPEC-03), woken by `LISTEN platform_events` and also polled every second.
- Each event is sent as `id: <seq>`, `event: <type>` and `data: <envelope JSON>`, with a comment every 15 s to keep proxies open.
- `Last-Event-ID` resumes after that sequence. The instance stream carries factory and configuration events.

**OpenAPI and client (REQ-1010).**
- `make gen` writes `packages/grindstone/openapi.json` from the app, sorted and stable. FF-02 fails on drift.
- FF-03 is extended to the document: removing a path, removing or changing a response field, or adding a required request field under `/api/v1` is breaking. It needs `/api/v2` (Components, "Contracts, versioning"); in M1 no such change is expected.
- `scripts/gen-api-client.mjs` writes `packages/contracts-ts/src/api.ts`: one typed function per operation, from each `operationId`, using the request and response types already generated from the same contracts (FF-02).

**Web shell (REQ-1011, REQ-1012).** `web/`, a SvelteKit static build (`adapter-static`) served by the control plane at `/` with a fallback page. It holds no secrets and no session token beyond the cookie.

| Page | Shows | Uses |
| --- | --- | --- |
| Login | Password form | session |
| Projects | List; create from pasted or uploaded TOML, with per-field errors | projects |
| Project | Configuration status; the open-decision queue; recent tasks | decisions, tasks, events |
| Decision card (by kind) | Title, flags, recommendation with its reason and source, the payload rendered by kind | decisions |
| Import | Upload a bundle; errors per item; link to the new decision | imports |
| Commands | Templates with argument forms from their JSON Schema; plan preview; start | templates, commands |
| Task | State timeline, runs with manifests, turns, checks with freshness and stale reasons, delivery with mode and status, transcript | tasks, events |

The decision card renders each kind:
- **`approval`:** revisions with field diffs against their current base; reached items, each with a verdict input (`unaffected` and a reason) required before approve, beside the note "if an item is affected, reject and draft a larger change" (the M1 thinning of SPEC-04's DEC-0402).
- **`question`:** a form from the answer schema for strings, enums and booleans, otherwise a JSON editor validated against the schema.
- **`permission`:** the action, the reason and the three answers.
- **`delivery`:** the evidence table with freshness, and the mode shown prominently, since ADR-40 requires it; in unenforced mode, the note that outside merges are detected only while a delivery is open (SPEC-08).
- **`escalation`:** the cause and the offered answers.

The card sends the context hash it rendered, so an answer to a changed decision is refused (SPEC-04) and the card reloads.

Package pins, each the latest on the npm registry on 17 October 2026: `@sveltejs/kit` 3.1.0, `svelte` 5.57.2, `@sveltejs/adapter-static` 4.0.0, `@sveltejs/vite-plugin-svelte` 7.3.1, `vite` 8.3.4, `svelte-check` 4.7.7, `@playwright/test` 1.64.1. `web/` pins `typescript` 6.0.3 (DEC-1003). The UI's graph component (`@xyflow/svelte`) arrives with SPEC-22.

**State and ownership.** Schema `surface`: `sessions`, `idempotency`. The `operators` table of the data model is not needed while there is exactly one operator whose credential is a secret file; SPEC-22 or SPEC-26 adds it if a second kind of credential needs one. SPEC-22 adds client tokens.

**Configuration** (`[surface]`, owned here): `cookie_secure` (false), `session_idle` (12 h), `session_max` (7 days), `login_failures_per_minute` (5), `sse_heartbeat` (15 s). The listeners themselves are SPEC-05's.

**Security.**
- B4: nothing before login except login and health. The login is rate-limited, sessions are server-side, the cookie is `SameSite=Strict`, and the CSRF header with no CORS headers means another origin cannot send it.
- The operator listener refuses the stations' network (SPEC-05).
- Payloads are rendered as text, never as HTML: Svelte escapes by default, and no `{@html}` is used. So item text and agent recommendations cannot script the page.

**Make and prove.** No subjects. Answers are the operator's, recorded by the decision service.

**Fitness functions.**
- FF-02 is extended to `openapi.json` and `api.ts`.
- FF-03 is extended to `/api/v1`.
- FF-07 covers schema `surface`.

## 6. Decisions

DEC-1001: Server-side sessions with an HMAC-stored identifier, not signed stateless cookies · Logout and expiry take effect at once, and a database dump yields no usable session · Rejected: signed cookies (no revocation without a deny list); bearer tokens in browser storage (readable by any script that runs in the page).
DEC-1002: A small generator writes the TypeScript REST client from the OpenAPI document onto the types already generated from the contracts · One source of types, no new dependency · Rejected: `openapi-typescript` 7.13.0 with `openapi-fetch` (their peer range is TypeScript 5, while the repository and SvelteKit are on 6 and 7).
DEC-1003: `web/` pins TypeScript 6.0.3 while the rest of the repository stays on 7.0.2 · `@sveltejs/kit` 3.1.0 and `svelte-check` 4.7.7 declare peer ranges that stop at TypeScript 6, the check `docs/m0/versions.md` asked SPEC-10 to make · Rejected: holding the repository at TypeScript 6 (gives up the native compiler elsewhere for one package); ignoring the peer range (an unsupported pair for the type checker the UI's CI relies on). ADR-46 allows the exception; `docs/m0/versions.md` records its constraint, and it is re-checked at every upgrade.
DEC-1004: The web shell is tested end to end with Playwright against the built stack · The cards are where the operator's authority is exercised, so they are tested as the operator uses them · Rejected: component tests only (would not catch a card answering the wrong decision or losing its context hash).

## 7. Tickets and acceptance criteria

TKT-1001: Login, sessions, CSRF, rate limit, error mapping, idempotency · implements REQ-1001, REQ-1002, REQ-1007, REQ-1008 · depends on TKT-0501, TKT-0201 · paths `packages/grindstone/src/grindstone/surface/`, `packages/grindstone/tests/surface/`.
TKT-1002: REST routes for projects, imports, items, ChangeSets, decisions, templates, commands, tasks, deliveries · implements REQ-1003 to REQ-1006 · depends on TKT-1001, TKT-0403, TKT-0601, TKT-0804 · surface paths plus `packages/grindstone/src/grindstone/contracts/api.py`.
TKT-1003: Event streams · implements REQ-1009 · depends on TKT-0304 · surface paths.
TKT-1004: OpenAPI document, drift and compatibility checks, generated client · implements REQ-1010 · depends on TKT-1002 · paths `scripts/`, `packages/grindstone/openapi.json`, `packages/contracts-ts/src/api.ts`, `tests/fitness/`.
TKT-1005: Web shell and its end-to-end tests · implements REQ-1011, REQ-1012 · depends on TKT-1004, TKT-1003 · paths `web/`, `pnpm-workspace.yaml`, `docker/grindstone.Dockerfile`.

AC-1001-1: Every route but login and health returns 401 without a session; a state-changing request with a session but without the CSRF header returns 403; no response carries an `Access-Control-Allow-Origin` header · verifies REQ-1001 · security · `test_routes_require_session_and_csrf`.
AC-1002-1: A hash written by `make secrets` (SPEC-05) verifies; a correct password creates a session whose stored row holds no raw identifier; the cookie is `HttpOnly` and `SameSite=Strict`; an idle session expires; the sixth failure within a minute returns 429 even with the right password · verifies REQ-1002 · security · `test_login_sessions_and_rate_limit`.
AC-1003-1: Importing a valid fixture bundle returns the ChangeSet and an open `approval` decision; an invalid one returns 422 with every item's errors · verifies REQ-1003 · integration · `test_import_endpoint`.
AC-1004-1: Answering an `approval` through the API with verdicts applies the ChangeSet and records channel `api` and the operator; answering with a stale context hash returns 409 `context_changed` · verifies REQ-1004 · integration · `test_answer_decision_endpoint`.
AC-1005-1: The plan preview for a fixture template lists its steps, needs, matched capabilities and checks without creating a task; starting the command creates the template run · verifies REQ-1005 · integration · `test_plan_preview_then_start`.
AC-1006-1: A task view after a scripted run shows the manifest, turns, a stale check with its reason named after a criterion edit, and the delivery's mode and state · verifies REQ-1006 · integration · `test_task_view`.
AC-1007-1: Repeating an answer, an import and a command with the same key returns the same response and creates nothing new; the same key with another body returns 422 `idempotency_key_reused`; killed after the effect and before storing the response, a retry returns the original result · verifies REQ-1007 · crash-and-resume · `test_commands_idempotent_on_client_key`.
AC-1008-1: For one code of each class, the response status matches the table and the body is an `ErrorEnvelope` · verifies REQ-1008 · contract · `test_error_status_mapping`.
AC-1009-1: A client that disconnects after sequence n and resumes with `Last-Event-ID: n` receives n+1 onward exactly once, in order, while events keep being written; a decision raised is delivered within 1 s · verifies REQ-1009 · integration · `test_event_stream_resume`.
AC-1010-1: Changing a route's response contract without `make gen` fails FF-02; removing a response field under `/api/v1` fails FF-03; the generated client type-checks against the contracts · verifies REQ-1010 · contract · `test_openapi_drift_and_compat`.
AC-1011-1: The web build contains no `{@html}` and imports no module but the generated client and its own components for data access; a decision payload with `<script>` in a title renders as text · verifies REQ-1011 · security · `test_web_shell_has_no_domain_logic_or_html_injection`.
AC-1012-1: Playwright, against the built stack with the scripted preset: log in, create the testbed-style fixture project, import its bundle, approve the card, preview and start the command, watch the task reach `delivering` without reloading, answer the `delivery` card, and see the task `done`; every update appears within 1 s of its event · verifies REQ-1012 · integration · `ui_m1_operator_flow.spec.ts`.

## 8. Test plan

- **Security:** AC-1001-1, AC-1002-1, AC-1011-1.
- **Integration**, on real Postgres and DBOS with the scripted preset and fake adapters: AC-1003-1, AC-1004-1, AC-1005-1, AC-1006-1, AC-1009-1, and AC-1012-1 with Playwright.
- **Crash-and-resume:** AC-1007-1.
- **Contract:** AC-1008-1, AC-1010-1.
- **Live run:** SPEC-09's M1-01 and M1-08 runs use this surface, as the operator would, at the M1 close.

## 9. Open items and risks

OQ-1001: Should the operator be able to change the password without restarting? · Default: no; rerun `make secrets` with a new password and restart `grindstone` · Resolved by SPEC-27's rotation runbook.
OQ-1002: Does the decision card need a diff view richer than field diffs for long text? · Default: a line diff of text fields · Resolved by the M1 live run's use, then SPEC-22.

Risks mitigated: unauthenticated or cross-site use of the operator's authority (session, CSRF, no CORS); answers to changed decisions (context hash from the card); duplicate commands from retries (client keys stored with their effects); missed or doubled UI updates (sequence-numbered, resumable stream).
Risk added: a second TypeScript version in the workspace. Mitigation: it is confined to `web/`, and moves to TypeScript 7 when SvelteKit's peer range allows.

## 10. Rollout

The first migration creates schema `surface`. `make gen` gains the OpenAPI document and the client. The control-plane image gains the static web build (a Node build stage; the runtime stays Python only). `docs/m0/versions.md` records the new pins. No stored data exists before M1.
