# SPEC-07 — Kernel MCP surface, first cut
Status: in review (revision 1 answers review 1, `docs/specs/reviews/SPEC-07-review-1.md`) · Milestone: M1
Kind: kernel · Owns: `grindstone.surface.mcp` (the kernel MCP server, per-task tokens, the M1 tool set and its schemas, the tool wrapper that counts open calls and sends keepalives)

Compact walking-skeleton specification (Planning playbook). Review: by a session that did not write it, then the operator.

## 1. Purpose

Agents act on Grindstone only through one narrow, typed surface scoped to their task (ADR-16). Everything else follows from that: agents propose and the kernel applies (I-03); configuration is out of reach (I-14); no agent reaches another (I-16). This specification builds that surface for M1: an MCP server inside the control plane, a token per task run and turn that the server checks on every request, and the tools a walking-skeleton agent needs:
- read its pinned inputs;
- report;
- propose items;
- ask the operator;
- request a permission.

Each refuses what it must with an error the agent can act on.

## 2. Scope

In scope:
- **Server and auth:** the FastMCP server on the station listener; per-task tokens, minted by `work` and verified per request.
- **Tools:** `read_item`, `read_items`, `read_blob`, `report`, `propose`, `ask` (operator only) and `request_permission`.
- **Wrapper and versioning:** the tool wrapper (scoping by mode and pins, structured errors, open-call counting, progress keepalives); generated tool schemas and the tool-set version.

Out of scope:
- `ask` to a specialist, `delegate`, `load_skill` and skill tools listed from session start (ADR-43): SPEC-17 (M3). In M1, `ask` with any need but `operator` returns `not_available`.
- `search`: SPEC-23 (M5).
- `read_items(query)` over the item graph: SPEC-11 (M2). In M1, `read_items` takes a list of IDs.
- What happens after a tool: report validation and suspension (SPEC-06), drafts (SPEC-04), decisions (SPEC-04).
- The operator's REST API and event stream: SPEC-10.

## 3. Foundation links

Implements:
- **ADR-16.** One MCP server inside the control plane (FastMCP), mounted per task run and authenticated by a per-task bearer token naming task, run and capability; every tool scoped to the task's pins and grants; no tool to apply, transition, deliver, change configuration or reach another task.
- **I-03.** The surface exposes report and propose, never apply.
- **I-10.** No tool turns what it returns into intent. Answers to the operator's questions enter the next prompt as context (SPEC-06), never as revisions.
- **I-14, I-16.** No tool reads or writes configuration, and no tool addresses another task or session.
- **I-11.** `ask` to the operator and `request_permission` raise typed decisions with the agent's recommendation.
- **ADR-38, in part.** The wrapper sends progress notifications at least every 30 s on any long call, because SPK-5 showed that this, not the wall-clock timeout, is what keeps Claude Code's call open. SPEC-17's consults rely on it.
- **ADR-43.** The tool list a session sees never changes after it starts. In M1 no skill tools exist; SPEC-17 adds them to the start list.

Delivers:
- **M1-03**, the refusal clause: "an invalid report is refused with structured errors" → AC-0704-1. SPEC-06 delivers fixing it in the same turn, the corrective prompt and the operator ask's suspension and resume. This specification's `ask` tool is what starts that suspension (AC-0706-1).

Depends on:
- **SPEC-01:** `ErrorEnvelope`, `ItemRef`, `BlobRef`.
- **SPEC-03:** registries (capabilities' modes and produced kinds), error codes.
- **SPEC-04:** `intent.read_pinned`, `render`, `allocate`, kind validation.
- **SPEC-05:** the station listener and the `mcp_token_key` secret.
- **SPEC-06** (part 2 for `work`, part 1 for `stations`): `work.context_for(run)` (task, mode, pins, capability, current turn and its state), `work.submit_report`, `work.suspend`, `work.add_proposals`, and the open-call registry in `stations`.

Scenarios: K1 step 4 (the agent reads N-3 through MCP and submits a report with a proposed revision and a declared file).

## 4. Requirements

REQ-0701: The kernel MCP server is served only on the station listener at `/kernel/mcp`, over MCP's streamable HTTP transport, by FastMCP mounted in the control plane's FastAPI application.
REQ-0702: Every request carries a bearer token that names project, task, run, turn and capability and is signed with the MCP token key; the server verifies the signature and that the token's turn is the run's current turn and is open, neither ended nor suspended, on every request, and refuses anything else with HTTP 401 before any tool runs.
REQ-0703: `read_item`, `read_items` and `read_blob` return only revisions and blobs pinned in the run's inputs, rendered as SPEC-04 renders them with the typed fields alongside, and refuse anything else with `not_pinned`.
REQ-0704: `report` submits the turn's report to `work`; an invalid report returns an error result whose structured content lists every violation with a JSON pointer, a rule and a message, and a second report after one was accepted returns `report_already_accepted`.
REQ-0705: `propose` accepts item revisions only in `work` mode and only of kinds the capability may produce, validates each against its kind contract, accepts references only to the run's pinned items and to items created in the same proposals, allocates IDs for kinds that allocate them, and adds them to the run's proposals; it never writes intent.
REQ-0706: `ask` with need `operator` requires a question, an answer schema and a recommended answer with its reason, and suspends the turn through `work`; with any other need it returns `not_available`.
REQ-0707: `request_permission` requires an action and a reason, and suspends the turn through `work` with a `permission` decision.
REQ-0708: The tool list is fixed for the M1 tool set `grindstone/1` and depends only on the task's mode; no tool applies, transitions, delivers, reads configuration or names another task.
REQ-0709: Every tool's input and output schema is generated from a Pydantic contract and checked for drift, and an incompatible change to a tool needs a new tool-set version.
REQ-0710: The wrapper counts each tool call as agent activity for its run, keeps a count of calls open per run for liveness, and sends a progress notification at least every 30 s while a call is open, when the client provided a progress token.
REQ-0711: Every refusal is a tool error result carrying an `ErrorEnvelope`; no tool raises an unstructured error to the agent, and an internal error is logged with its correlation IDs and returned as `invariant_violated` without details.

## 5. Design

**Mounting.** As SPK-1, experiment 3, ran it: `mcp_app = mcp.http_app(path="/mcp")`, mounted at `/kernel` on the station application, whose lifespan includes `mcp_app.lifespan`. A pure ASGI middleware in front of the mount checks the bearer token on every HTTP request, not only at session start. A tool reads the verified claims from the request scope; FastMCP's `get_http_headers()` is not trusted on its own. Pins: `fastmcp==4.1.0` and `mcp==2.3.0`. Both are the latest on PyPI on 17 October 2026, and FastMCP requires `mcp>=2.0,<3`. Claude Code speaks MCP revision `2026-07-28` with one POST per request (SPK-5).

**Tokens (REQ-0702).**
- **Minting:** `mint(task, run, turn, capability, project)` returns `base64url(claims) + "." + base64url(HMAC-SHA256(mcp_token_key, claims))`, where `claims` is the RFC 8785 canonical JSON of `{v: 1, project, task, run, turn, capability, iat}`. `work` mints one per turn (SPEC-06) through this function, which the composition root registers with `work`, because `work` may not import `surface`.
- **Verification**, on every request:
  1. decode the token and check the signature in constant time;
  2. call `work.context_for(run)` to check that the run is `active`, its current turn equals `turn`, and that turn is `open` (SPEC-06 part 2, REQ-0627).
- **Lifetime:** a token dies when its turn ends or suspends, so a session disposed after a suspension, or an orphaned agent process, can do nothing with an old token.
- **Revocation:** there is no list. A run or turn that ends is revoked by state.

**Tools** (tool set `grindstone/1`, advertised as the server's version and in its instructions):

| Tool | Modes | Input | Result |
| --- | --- | --- | --- |
| `read_item` | all | `id` | `{id, kind, title, hash, fields, markdown}` of the pinned revision |
| `read_items` | all | `ids` (≤ 100) | A list as above; per-ID errors inline |
| `read_blob` | all | `hash` | Media type, size and content (text, or base64 for binary), ≤ 8 MiB; larger blobs return `blob_too_large` |
| `report` | all | `outcome` (`done`, `blocked`, `failed`), `summary` (≤ 8 KiB), `data` (the capability's report schema), `files` (relative paths: no absolute path, `..` segment or NUL byte, each ≤ 1,024 bytes, refused by the contract) | `accepted`, or an error result listing violations |
| `propose` | `work` | `items`: kind, ID or none (to allocate), title, fields, base hash for a revision | Each item's ID and status, or its errors |
| `ask` | `work` | `need`, `question` (≤ 8 KiB), `refs` (pinned IDs), `answer_schema` (JSON Schema), `recommendation` (`answer`, `reason`) | For `operator`: the decision ID and "your turn is suspended; end it now" |
| `request_permission` | all | `action`, `reason`, `recommendation` | The decision ID and "your turn is suspended; end it now" |

Notes:
- `read_item` returns a pinned revision even if the item has moved on since. SPEC-16 delivers new revisions at the next turn.
- `report` with `files` lists the paths it produced; SPEC-06's collect checks them against the output contract.
- `propose` stores the items on the run; they become one ChangeDraft at collect (SPEC-06).

**Errors.** Registered here:
- validation: `not_pinned`, `kind_not_produced`, `blob_too_large`, `tool_not_in_mode`;
- limit: `not_available`.

The tools also return codes owned by SPEC-04 (`reference_unresolved`, `id_invalid`, `recommendation_missing`) and SPEC-06 (`report_invalid`, `report_already_accepted`). An error result is MCP's `isError: true`, with the `ErrorEnvelope` as structured content and its message as text, so an agent that reads only text still sees the reason.

**Wrapper (REQ-0710, REQ-0711).** One decorator wraps every tool:
1. resolve the context from the verified claims;
2. refuse a tool outside the mode (`tool_not_in_mode`);
3. record activity (`stations.touch(run)`);
4. increment `stations.open_calls[run]` and decrement it in `finally`;
5. start a 30 s progress timer when the request has a progress token;
6. map known errors to envelopes and anything else to `invariant_violated`, logged with project, task, run, turn and request IDs.

The open-call registry lives in `stations`, in process memory. It needs no persistence, because a restart ends every open call.

**Schemas (REQ-0709).**
- Tool inputs and outputs are contracts in `grindstone.contracts.mcp`. FastMCP derives tool schemas from them.
- `make gen` writes the tool list with its schemas to `packages/grindstone/mcp-tools.json`, and FF-02 fails on drift.
- FF-03 is extended to that file. Removing a tool, or changing a tool's input incompatibly, needs a new tool-set version (`grindstone/2`) and an upgrade note. Capabilities declare the tool set they support (Components, "Contracts, versioning"), and SPEC-17 adds that declaration with its new tools.

**State and ownership.** No tables. Proposals are stored by `work`, decisions by `decisions`, open-call counts by `stations` in memory.

**Behaviour.**
- The tools themselves have no external effects. `ask` and `request_permission` write a decision and a report through `work.suspend` in one unit of work.
- A repeated call is handled by the services: a second `report` is refused, and a second `ask` in a suspended turn finds its token dead.

**Interfaces.** MCP tools as above. Python: `surface.mcp.mint(...)`, `surface.mcp.app`.

**Configuration.** `[surface].mcp_max_blob_bytes` (8 MiB) and `[surface].mcp_keepalive_seconds` (30), both owned here.

**Security.**
- B1: the token is the only way in, verified per request against live state. Tokens are bound to one run and one turn.
- Arguments are untrusted. Every one is validated by its contract, with size bounds, before any service sees it.
- Tool results carry only pinned content, so no content from another task, project or configuration can be read.
- The surface is served only on the station listener, which the operator listener does not expose (SPEC-05).

**Make and prove.** No subjects. The surface cannot record evidence: no tool writes to `evidence`. Reviewers' verdicts arrive as reports of `check`-mode tasks, which SPEC-08 turns into evidence for the subject.

**Fitness functions.**
- FF-02 is extended to `mcp-tools.json`, and FF-03 to tool compatibility.
- The tool-list test (AC-0708-1) is the architecture test I-16 names for this surface: no tool reaches another task.

## 6. Decisions

DEC-0701: Tokens are HMAC-signed claims checked against live run state on every request · The claims name the task, run, turn and capability as ADR-16 requires, and revocation needs no table because an ended turn is a dead token · Rejected: opaque random tokens in a table (a lookup per request and a second source of truth for run state); tokens per run rather than per turn (a disposed session's process could keep acting until the run ends).
DEC-0702: `ask` to the operator returns at once and suspends; it never holds the call open · A person may answer in days. ADR-14 frees the lane, and SPK-5 showed that a held call needs keepalives the agent cannot outlast · Rejected: holding the call open for the operator (a lane held for days).
DEC-0703: Error results carry the envelope as structured content and its message as text · Agents differ in which they read; both carry the same code · Rejected: protocol-level JSON-RPC errors (agents treat them as failures of the server, not as results to act on).
DEC-0704: `request_permission` suspends the turn like `ask` to the operator · A person may take days to answer a permission too, and the lane rule DEC-0702 applies is the same; foundation v4.6 lists it among the suspending tools · Rejected: holding the call open for the decision (a lane held while a person decides).
DEC-0705: References in proposals are limited to pinned items and items created in the same proposals · Otherwise `reference_unresolved` would tell an agent whether an unpinned ID exists, a probe outside its task's scope · Rejected: resolving against the whole project (the probe); hiding the code (a valid reference outside the pins would look like a typo).

## 7. Tickets and acceptance criteria

TKT-0701: Server mount, token minting and verification, tool wrapper · implements REQ-0701, REQ-0702, REQ-0710, REQ-0711 · depends on TKT-0601, TKT-0501 · paths `packages/grindstone/src/grindstone/surface/mcp/`, `packages/grindstone/tests/surface/`, `pyproject.toml` (fastmcp).
TKT-0702: The M1 tools and their contracts · implements REQ-0703 to REQ-0708 · depends on TKT-0701, TKT-0603 · same paths plus `packages/grindstone/src/grindstone/contracts/mcp.py`.
TKT-0703: Generated tool schemas, FF-02 and FF-03 extensions · implements REQ-0709 · depends on TKT-0702 · paths `scripts/`, `packages/grindstone/mcp-tools.json`, `tests/fitness/`.

AC-0701-1: `/kernel/mcp` answers on the station listener and returns 404 on the operator listener · verifies REQ-0701 · integration · `test_mcp_served_on_station_listener_only`.
AC-0702-1: In memory: a call with no token, a forged signature, another run's token, a token for a turn that has ended, or a token whose turn suspended, is refused with 401 before any tool code runs; a valid token works; a token minted for task A cannot read task B's pins · verifies REQ-0702 · in-memory tool · `test_per_task_token_scope`.
AC-0703-1: `read_item` returns the pinned revision of a pinned fixture item even after a later revision is applied, and refuses an unpinned ID with `not_pinned`; `read_blob` refuses an unpinned hash and a blob over the limit · verifies REQ-0703 · in-memory tool · `test_reads_are_scoped_to_pins`.
AC-0704-1: `report` with a missing required field and a wrong type returns an error result whose envelope lists both violations with JSON pointers; `files` with `../x`, `/etc/x` or a NUL byte is refused by the contract; after an accepted report, another returns `report_already_accepted` · verifies REQ-0704 · in-memory tool · `test_invalid_report_structured_errors`.
AC-0705-1: In a `check`-mode task `propose` returns `tool_not_in_mode`; in `work` mode, a kind the capability does not produce returns `kind_not_produced`; a valid proposal of an allocating kind gets an allocated ID; a reference to an existing but unpinned ID is refused like a missing one; no revision exists in `intent` afterwards · verifies REQ-0705 · in-memory tool · `test_propose_never_writes_intent`.
AC-0706-1: `ask` with need `operator` and no recommendation is refused with `recommendation_missing`; with one, it returns a decision ID and the turn is suspended; with need `notes.style` it returns `not_available` · verifies REQ-0706 · in-memory tool · `test_ask_operator_only_in_m1`.
AC-0707-1: `request_permission` without a reason is refused; with one it raises a `permission` decision and suspends the turn · verifies REQ-0707 · in-memory tool · `test_request_permission_suspends`.
AC-0708-1: The tool list for each mode equals the table's, and no listed tool's name or schema offers apply, transition, deliver, configuration or another task's ID · verifies REQ-0708 · in-memory tool · `test_tool_list_is_the_m1_set`.
AC-0709-1: Changing a tool's input contract without `make gen` fails FF-02; removing a field from a tool's input without a new tool-set version fails FF-03 · verifies REQ-0709 · contract · `test_mcp_tool_schemas_drift_and_compat`.
AC-0710-1: A test-only slow tool held open 95 s sends at least three progress notifications to a client that gave a progress token; while it is open, `stations.open_calls(run)` is 1, and after it returns, 0 · verifies REQ-0710 · in-memory tool · `test_open_calls_and_keepalives`.
AC-0711-1: A tool that raises an unexpected exception returns `invariant_violated` with no internal detail, and the log line carries the run and request IDs · verifies REQ-0711 · in-memory tool · `test_internal_errors_are_structured`.

## 8. Test plan

- **In-memory tool tests**, with FastMCP's in-memory client against the real tools and a real database: AC-0702-1, AC-0703-1, AC-0704-1, AC-0705-1, AC-0706-1, AC-0707-1, AC-0708-1, AC-0710-1, AC-0711-1.
- **Integration:** AC-0701-1.
- **Contract:** AC-0709-1.
- SPEC-06's scripted-agent tests exercise the same tools through the real host and Claude Code's transport shape.

## 9. Open items and risks

OQ-0701: Should `read_items` cap at 100 IDs? · Default: yes; M1 tasks pin a handful of items · Resolved by SPEC-11, which adds queries.
OQ-0702: Does every agent read MCP structured content on error results? · Default: the message text carries the code too (DEC-0703) · Resolved by the scripted-agent and live runs at the M1 close.

Risks mitigated: token reuse across tasks or after a turn (per-turn, state-checked tokens); agents reaching apply, configuration or other tasks (fixed tool list, tested); silent tool failures (structured errors only).
Risk added: a per-request database check adds latency to every tool call. Mitigation: one indexed read of the run row; M1 makes tens of calls a turn.

## 10. Rollout

`fastmcp` and `mcp` are pinned in `pyproject.toml` and recorded in `docs/m0/versions.md`. Tool set `grindstone/1` is the first. No stored data.
