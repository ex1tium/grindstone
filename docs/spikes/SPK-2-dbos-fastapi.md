# SPK-2 — DBOS in FastAPI

Status: done · Box: 2 days · Settles: the assumption that DBOS survives kills during steps, waits and child workflows without duplicate effects (Architecture, "Constraints, assumptions and capacity"); the lane design in ADR-03

## Why

QG-2 (durability) rests on DBOS Transact running every workflow in-process, with workflow and step IDs as idempotency keys (ADR-03). M1-04 kills the control plane between every external action and its record. This spike proves the mechanism before SPEC-02 and SPEC-06 depend on it.

## Setup

DBOS 3.3.0 in the lifespan of a FastAPI app, one uvicorn worker, PostgreSQL 18.6 from `compose.yaml`. A fake external service, a small HTTP server outside the app, records every request with its idempotency key, so duplicates are counted, not guessed. A harness kills the app with SIGKILL at a named point and restarts it.

## Experiments

1. **Kill during a step**, between the external call and the step's completion record. *Pass:* after restart the step re-runs, the fake service sees the same idempotency key twice, and our lookup-by-key records the effect once. This is the pattern every external step uses (Failure model).
2. **Kill during a message wait** (`recv`), and during `sleep`. *Pass:* the workflow resumes waiting; a message sent while the app was down is delivered exactly once.
3. **Kill during a child workflow**, both in the child and in the parent while it waits on the child. *Pass:* no second child is started; the parent receives the child's result once.
4. **Kill during a scheduled run.** *Pass:* the schedule fires once per period, with no duplicate after recovery.
5. **Idempotent messages.** Send the same message twice with the same idempotency key. *Pass:* delivered once.
6. **Serialized writing lane.** A queue with global concurrency 1 shared by workflows from different projects. *Pass:* never two running at once, under 50 enqueued from parallel requests.
7. **Parent on the writing lane waits for a child on the read-only lane.** *Pass:* no deadlock; the read-only lane's concurrency is honoured. Then, per v4.1 of the foundation, check the variant that matters most: the parent's turn **ends** when it delegates and the child runs on the **writing** lane the parent freed.
8. **Application-version bump with a parked workflow.** Start a workflow that parks waiting on a message, change the application version, restart. DBOS recovers pending workflows only on executors with a matching application version; record exactly how DBOS 3.3.0 behaves and which mechanism moves a waiting workflow across versions. *Pass:* the parked workflow resumes exactly once after the bump. This decides how SPEC-02 handles upgrades (M5-06). ADR-03 already keeps waits on people outside workflows (a decision stores a typed continuation); confirm that this design needs nothing more from DBOS than starting the continuation.
9. **Throughput sanity.** 500 short workflows (the capacity envelope's task runs per day, compressed) with steps writing to PostgreSQL. Record the DBOS overhead per step.

## Record

DBOS, FastAPI, uvicorn and psycopg versions; the lifespan code; the kill harness; per-experiment duplicate counts; DBOS's system-table schema size after experiment 9.

## Fallback

No alternative engine in the MVP (ADR-03). A failure is fixed in how Grindstone uses DBOS before the M1 specifications are written, and recorded in SPEC-02.

## Report (17 October 2026)

**Every experiment passed: DBOS survives SIGKILL during steps, waits, child workflows and scheduled runs with no duplicate effect, and the lanes behave as ADR-03 needs.** Two findings shape SPEC-02: version bumps strand workflows that are in flight, and the async lifespan needs DBOS's `_async` calls.

How it ran: in a Claude Code cloud session. Python 3.14.8; DBOS 3.3.0; FastAPI 0.143.3; uvicorn 0.54.0 with one worker; psycopg 3.3.6; SQLAlchemy 2.1.5, which DBOS pulls in. PostgreSQL 18.6 ran in Docker from the pinned `compose.yaml` image. The spike code is in `spk2/` on branch `claude/youthful-franklin-oq4j5j` of `ex1tium/grindstone-testbed` (never merged), with results in `spk2/results/20261017T161459Z/`. The harness gives each experiment a fresh system database, starts the app as `uvicorn app:app --workers 1`, and kills it with SIGKILL, either from outside or at a named point inside a step (`SPK2_KILL_AT`), so no shutdown hook runs. Every external call goes to a fake service that counts requests per idempotency key and records each effect once.

The lifespan:

```python
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    DBOS(config={"name": "spk2", "system_database_url": DB, "application_version": VERSION})
    DBOS.launch()
    await DBOS.register_queue_async("writing", global_concurrency=1)
    await DBOS.register_queue_async("readonly", global_concurrency=2)
    yield
    DBOS.destroy()
```

### Results

| # | Result | Evidence |
| --- | --- | --- |
| 1 | pass | Killed after the external call and before the step's record. After restart the step ran again, and the service saw the key `<workflow>:effect` twice but recorded the effect once. The workflow finished `done`. This confirms the Failure model's pattern: steps are at least once, and the key makes the effect once. |
| 2 | pass | `recv`: killed while waiting; a message sent through `DBOSClient` while the app was down was delivered after restart, once. `sleep(6)`: killed 2 s in and down 2 s, the workflow finished 1.0 s after the restart, sleeping 0.0 s in the recovered run. The deadline is durable: a restarted sleep would have taken 6 s. |
| 3 | pass | (a) Killed inside the child after its call: one child (`<parent>-1`), whose effect was called twice and recorded once; the parent got the result once. (b) Killed while the parent waited in `get_result`: after restart, still one child with the same deterministic ID, and every effect once. |
| 4 | pass | A six-field cron every 3 s, killed inside a run, down 8 s, up 12 s. Each period has one workflow ID, `sched-<schedule>-<time>`. The killed run's step ran twice and was recorded once; all runs `SUCCESS`. Periods missed while down were skipped, because `automatic_backfill` defaults to off. |
| 5 | pass | `send(..., idempotency_key="k1")` twice: the first `recv` got the message, and a second `recv` timed out with `None`. |
| 6 | pass | Queue `writing` with `global_concurrency=1`: 50 workflows from two projects, enqueued from 50 parallel HTTP requests, all finished, never more than one running. |
| 7 | pass | Three writing-lane parents, each waiting on a read-only child, plus five read-only runs: all finished with no deadlock. Peak writing 1; peak read-only 2, its limit. **Delegation** (v4.1): a writing parent enqueues its child on the writing lane and ends; each child started after the parents freed the lane, peak 1. **Control**: a writing parent that waits on a writing-lane child deadlocks. It was still `PENDING` after 8 s with its child `ENQUEUED`, until cancelled. So a turn must end when it delegates on the lane it holds. |
| 8 | pass, with a design consequence | Three workflows parked in `recv` on version `v1`; the app was killed and restarted as `v2`. **They are not recovered**: `v2` recovers and dequeues only `v2` workflows (`get_pending_workflows` filters on `application_version`), so they stay `PENDING`, and a message sent to one changes nothing. Two ways to move one across versions: **`fork_workflow(id, start_step, application_version="v2")`** gives a new workflow ID whose mailbox is not copied; it waits until a message is sent to the new ID, then finishes on `v2`. **`cancel_workflow` + `rewind_workflow(id, start_step=…, application_version="v2")`** keeps the ID, but a message sent before the rewind is deleted with the discarded history, and the workflow waited until a second message came. **ADR-03's shape**, where the wait lives outside the workflow and the answer starts a continuation, needs nothing from DBOS beyond starting a workflow on the current version: it finished on `v2` with one effect. |
| 9 | recorded | 500 workflows run one after another, each of two steps that write a row to PostgreSQL: 22.6 s, against 10.8 s for the same writes without DBOS. That is 11.8 ms of DBOS overhead per step, or 45 ms per workflow, on this session's Docker PostgreSQL, where every commit costs about 10 ms. The capacity envelope needs about 500 task runs a day, so this is not a constraint. After it, the system schema is 1.4 MiB (`operation_outputs` 1,002 rows; `workflow_status`, `workflow_input`, `workflow_output` about 500 each). |

### What this settles, and what SPEC-02 must take from it

- **The durability assumption holds** (QG-2, QS-04): kills during steps, `recv`, `sleep`, child workflows and scheduled runs cause no duplicate effect, as long as every external step carries an idempotency key derived from the workflow ID and step, and the target finds or creates by it. A step itself runs at least once.
- **Child workflow IDs are deterministic** (`<parent>-<step id>`), so recovery never starts a second child.
- **Scheduled workflows** are deduplicated by an ID per period. Missed periods are skipped unless `automatic_backfill` is set; SPEC-02 should choose per schedule.
- **Lanes**: a global-concurrency-1 queue serializes the writing lane across projects. A parent may wait on a read-only child, but never on a child on the lane it holds: it delegates and ends its turn (as v4.1 says).
- **Versions (decides SPEC-02's and SPEC-27's upgrade path, M5-06).** DBOS recovers and dequeues only workflows of its own `application_version`. When none is set, the version is an MD5 of the workflow source, so any change to workflow code strands every workflow in flight. SPEC-02 should therefore (1) set `application_version` explicitly, to a workflow-compatibility version that changes only when workflow code changes incompatibly, not on every release; and (2) on such a change, drain before upgrading: stop new work and let in-flight workflows finish or park. A parked wait on a person survives any upgrade because it lives outside the workflow (ADR-03). Waits inside workflows (agent turns, check jobs) are capped, so draining is bounded. `fork_workflow` is the escape hatch for a stuck one, with the message re-sent to the new ID. This is a proposal for SPEC-02's review, not decided here.
- **FastAPI integration**: inside the async lifespan, DBOS refuses its synchronous calls while the event loop runs (`register_queue() was called while an event loop is running`); use `register_queue_async` and `apply_schedules_async`. `DBOS.launch()` is allowed there. In 3.3.0, queues are not constructed directly but registered in the system database with `DBOS.register_queue` and found with `DBOS.retrieve_queue`.
- **Out-of-process control**: `DBOSClient` talks only to the system database, so it can send messages, read events, list, cancel, fork and rewind workflows, and manage schedules while the app is down.
