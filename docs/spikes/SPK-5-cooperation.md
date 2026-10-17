# SPK-5 — Cooperation mechanics

Status: planned · Box: 2 days · Settles: Q-9 configuration under ADR-38; `load_skill` behaviour (ADR-39); consult cost and latency

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
