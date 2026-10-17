# SPK-2 — DBOS in FastAPI

Status: planned · Box: 2 days · Settles: the assumption that DBOS survives kills during steps, waits and child workflows without duplicate effects (Architecture, "Constraints, assumptions and capacity"); the lane design in ADR-03

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
