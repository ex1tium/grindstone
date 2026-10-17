# SPK-5 — Cooperation mechanics

Status: done · Box: 2 days · Settles: Q-9 configuration under ADR-38; `load_skill` behaviour (ADR-39); consult cost and latency

## Why

ADR-38 holds a consult's `ask` call open until the consult answers, under a ceiling (seed 2 hours), with MCP progress notifications as keepalives and each agent's client tool timeout raised by configuration. This spike measures whether that holds for Claude Code, and what to configure; each further agent repeats it when added (ADR-41).

## Setup

The SPK-1 host and stub kernel MCP server, extended with an `ask` tool whose answer arrives after a controllable delay, and a consult cache keyed by `(capability hash, question hash, input hashes)`.

## Experiments

1. **Long open call.** `ask` answers after 2, 10, 30 and 120 minutes, with progress notifications every 30 seconds. For each agent, record the client-side MCP tool timeout and how to raise it by configuration, whether progress notifications reset it, any server or proxy idle timeout, and whether the model itself abandons the call. *Pass:* with configuration, Claude Code receives the 120-minute answer in the open call.
2. **Without keepalives.** Repeat at 10 minutes with no progress notifications. Records how much the keepalives matter.
3. **Dropped session, single-flight join.** Kill the session 5 minutes into a 30-minute consult; start a new session on the same workspace and ask the same question. *Pass:* the second ask joins the in-flight consult; one consult run in total; the answer arrives once.
4. **Ceiling.** Set the ceiling to 5 minutes and the consult to 10. *Pass:* at 5 minutes the call returns `consult_ceiling`, the turn suspends with outcome waiting, and the answer at 10 minutes resumes the run in a new session with the answer in context.
5. **Liveness while waiting** (ADR-37). With a 2-minute liveness timeout and a 10-minute consult. *Pass:* the waiting caller is not failed as `stalled`; a session that goes silent with no open tool call is.
6. **`load_skill` inline** (ADR-39). Mid-session, `load_skill` returns a skill's instructions as the tool result and adds a tool. *Pass:* the agent follows the instructions and can call the added tool; record how the tool is added (an MCP `tools/list_changed` notification, or otherwise).
7. **Cost and latency.** Cached and uncached consults on the fixture project: wall time, turns, tokens where reported.

## Record

Per agent and version: the timeout settings and values; whether progress resets them; the ceiling behaviour; latency numbers.

## Fallback

For an agent whose client cannot hold a call open, consults park and resume (ADR-38).

## Report (17 October 2026)

**ADR-38 holds for Claude Code with one setting, and the cache and single-flight join work. One finding changes ADR-39: Claude Code never sees a tool added mid-session.** The longest open call was shortened from 120 to 45 minutes (decided with the operator), because every timer except the overall wall-clock limit is 30 minutes or less. So ADR-38's 2-hour seed ceiling rests on a 45-minute run, a 10-minute run on default settings, and the documented wall-clock default. Re-check 2 hours once on the stable host before relying on it.

How it ran: in a Claude Code cloud session, on the SPK-1 host (Claude Code 2.1.300 through `claude-agent-acp` 0.93.0) and a stub kernel (FastMCP 4.1.0 in FastAPI). Every experiment ran at once, at real durations: 17:25–18:11 UTC, keepalives every 30 s. Code and record: `spk5/` on branch `claude/youthful-franklin-oq4j5j` of `ex1tium/grindstone-testbed` (never merged), `spk5/results/full/record.json`.

### Claude Code's timers (documentation of 17 October 2026, then measured)

| Timer | Default | Set by | Progress notifications |
| --- | --- | --- | --- |
| Wall clock per tool call | about 28 h | `MCP_TOOL_TIMEOUT`, or a per-server `timeout` | do not extend it |
| Idle window | 5 min for HTTP, 30 min for stdio | `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` (0 disables) | **reset it** (measured) |
| First response byte (HTTP only) | the greatest of 60 s, the tool timeout and `MCP_TIMEOUT` | the same | an SSE response with progress answers it early; never tripped |
| Auto-background of a long call | after 2 min | `CLAUDE_CODE_MCP_AUTO_BACKGROUND_MS` | — |

Auto-backgrounding never applies here: the documentation excludes non-interactive and SDK sessions unless `CLAUDE_AUTO_BACKGROUND_TASKS=1`, and it never happened through `claude-agent-acp`. Claude Code sends a progress token on every call. It speaks MCP revision `2026-07-28` to an HTTP server, one POST per request.

### Results

| # | Result | Evidence |
| --- | --- | --- |
| 1 | pass | Keepalives every 30 s and `MCP_TOOL_TIMEOUT` = 3 h. Calls held open for 2, 10, 30 and 45 minutes all returned the answer in the open call: the 45-minute one after 89 progress notifications. **On Claude Code's defaults** (no variable set), the 10-minute call also returned, after 19 notifications, so the defaults already hold a call open for about 28 hours as long as keepalives come more often than every 5 minutes. The model never abandoned a call. |
| 2 | pass (as expected) | Without keepalives, the 10-minute call was aborted by Claude Code at 300 s: `MCP server "grindstone" tool "ask" sent no response or progress for 300s; aborting`. **The server never learned the call was gone:** it kept holding it and "delivered" the answer at 600 s to nobody. A client-side abort does not cancel the request on the server, so the kernel must not count a delivery as received (see below). |
| 3 | pass | Session J1 asked a 30-minute consult; at 5 minutes the session was disposed through AHP (`disposeSession`): its turn ended `chat/turnCancelled`, and the kernel saw the call cancelled (`CancelledError` at 288 s held). A new session J2 on the same workspace asked the same question: **joined** the in-flight consult (one consult, `runs: 1`) and received the answer once, at 30 minutes. |
| 4 | pass | Ceiling 5 min, consult 10 min. At 300 s the call returned `consult_ceiling`; the agent replied `WAITING` and its turn ended (the control side records outcome waiting). The consult kept running; at 611 s its answer arrived and the run resumed in a new session with the answer in its prompt, which wrote it to the workspace. The waiting caller never received a second delivery (`delivered: 0` for that consult). |
| 5 | pass | Liveness 2 min, rule "no AHP activity for the window **and** no open kernel call". The callers holding open `ask` calls for up to 45 minutes were never flagged, although AHP shows nothing new while a call is open: the open kernel call is what keeps them live. A session whose agent processes were stopped mid-turn (SIGSTOP, no open kernel call) was flagged after 125 s of silence. So the kernel's open-call count is the pause signal ADR-37 needs; AHP events alone are not. |
| 6 | **fail for Claude Code** | `load_skill` returned the skill's instructions inline, and the agent read them and tried to follow them. The tool they named, enabled for that MCP session with FastMCP's `ctx.enable_components` (which sends `tools/list_changed`), **never reached the agent**, in that turn or the next. The kernel's request log shows Claude Code listing tools before calling `load_skill`, then never again, and never opening a GET stream on which a notification could arrive. Its `ToolSearch` searches the list it already holds. |
| 7 | recorded | A consult answered by a real Claude Code session on the fixture project ("which functions does `src/testbed/text.py` define?"): the consult itself took **4.0 s**, 1 tool call, 16,953 tokens in context, **$0.028** (reported by `claude-agent-acp`, Sonnet 5.5). The asking turn took 18.8 s end to end. The same question from another session was a **cache hit**: the asking turn took 6.3 s, and the consult cost nothing. |

### What to configure, and what to change

- **ADR-38's settings for Claude Code:**
  - The kernel sends progress at least every 30 s while an `ask` is open. That is what holds the call: the 5-minute idle window is the binding limit, and progress resets it.
  - Set `MCP_TOOL_TIMEOUT` explicitly to the capability's ceiling plus a margin, through the agent's environment in the host wrapper. The default (about 28 h) is already above the 2-hour seed, but stating it makes a later default change visible.
  - Leave `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` at its default, so a silent server still fails fast.
  - Never set `CLAUDE_AUTO_BACKGROUND_TASKS`.
  - The ceiling (`consult_ceiling`) and the resume in a new session work as specified.
- **Deliveries must be acknowledged, not assumed.** An aborted or disposed call is not always seen by the server (experiment 2 saw nothing; experiment 3 saw the cancellation). The kernel should treat an answer as delivered only when the turn that holds it continues; the consult's cache keeps the answer for the next ask either way.
- **Liveness pauses on the kernel's open-call count** (experiment 5), not on AHP activity.
- **ADR-39, proposed change (for SPEC-17 or the kernel MCP specification):** Claude Code does not pick up tools added mid-session. `load_skill` should keep returning instructions inline, and the tools of every skill in the capability's library should be listed from session start, with the kernel refusing a call to a skill tool until its skill is loaded: `skill_not_loaded`, telling the agent to call `load_skill`. The tool list stays fixed for the session, and loading changes only what the kernel allows. An alternative is one fixed `skill_tool(skill, tool, arguments)` dispatcher, which keeps the listed surface small when libraries are large. This changes ADR-39's "adds its declared tools": accepted as ADR-43 (foundation v4.5).
- **Cost:** a cached consult costs nothing and saves the consult's wall time; an uncached small consult on the fixture project cost $0.03 and 4 s. At these sizes the cache matters for latency more than for spend.
