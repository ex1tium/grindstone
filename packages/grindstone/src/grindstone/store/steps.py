"""External steps: the idempotency key, the step registry and kill points.

A workflow step with an effect outside the database runs at least once: DBOS
checkpoints a step only after it returns, so a crash between the effect and
the checkpoint re-runs the step on recovery. The rule that makes a crash cost
time, never a duplicate (SPEC-02, REQ-0204, QS-04):

- Every workflow started for a record takes that record's ID as its first
  input (`start` checks it). `external_step(name, effect=...)` wraps
  `DBOS.step` and passes the step an `IdempotencyKey`,
  `<causing record ID>:<step name>[:<n>]`, built from that input. A fork
  copies the inputs, so a step re-executed under a forked workflow ID gets the
  same key. The DBOS workflow ID is never part of a key.
- The step hands the key to its target, which finds the earlier effect by it,
  or by a lookup on the causing record that the target documents, before it
  creates one: the agent host by client key, a delivery adapter by its
  documented lookup, the blob store by content hash.

Every external step is registered with its name, owning module, effect and
kill points (REQ-0213). FF-10 (`scripts/ff/idempotency.py`) reads the same
declarations from the source and fails while a step has no key or no
crash-and-resume scenario; the crash matrix (`tests/crash/`) kills the control
plane at every registered point of every registered step and restarts it.

`kill_point(name)` is the harness's hook: with `GRINDSTONE_KILL_AT=<name>` it
kills the process the first time execution reaches that point, leaving the
marker file `GRINDSTONE_KILL_MARKER` names so that the restart runs through.
Each external step has, by default, `before:<step>` (before the effect) and
`after:<step>` (between the effect and its checkpoint).
"""

import contextvars
import functools
import inspect
import os
import signal
import sys
from collections.abc import Awaitable, Callable, Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Concatenate, cast, override

from dbos import DBOS

KILL_AT_ENV = "GRINDSTONE_KILL_AT"
KILL_MARKER_ENV = "GRINDSTONE_KILL_MARKER"

# The ID of the record that caused the running workflow: its first input.
_record: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "grindstone_causing_record", default=None
)


@dataclass(frozen=True, slots=True)
class IdempotencyKey:
    """`<record>:<step>[:<n>]`: what an external step's target finds its earlier effect by.

    `n` tells apart repeated effects of one step for one record, such as a
    step a workflow runs once per turn.
    """

    record: str
    step: str
    n: int | None = None

    @override
    def __str__(self) -> str:
        suffix = "" if self.n is None else f":{self.n}"
        return f"{self.record}:{self.step}{suffix}"


@dataclass(frozen=True, slots=True)
class ExternalStepSpec:
    """A registered external step, as FF-10 and the crash matrix read it."""

    name: str
    module: str
    effect: str
    kill_points: tuple[str, ...]


class _Registry:
    """External steps registered through `external_step`, by name."""

    steps: dict[str, ExternalStepSpec]

    def __init__(self) -> None:
        self.steps = {}


_registry = _Registry()


def default_kill_points(name: str) -> tuple[str, ...]:
    """`before:<name>` and `after:<name>`: before the effect, and between it and the checkpoint."""
    return (f"before:{name}", f"after:{name}")


class ExternalStep[**P, R]:
    """A registered external step; calling it runs the DBOS step with its key.

    Call it inside a workflow registered through `workflow` and started with
    `start`, whose first input is the causing record's ID. `nth(n)` gives the
    same step keyed `<record>:<step>:<n>`.
    """

    __slots__ = ("_step", "spec")

    def __init__(self, spec: ExternalStepSpec, step: Callable[..., object]) -> None:
        self.spec = spec
        self._step = step

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        return cast(R, self._step(self.key(), *args, **kwargs))

    def nth(self, n: int) -> Callable[P, R]:
        """The step keyed `<record>:<step>:<n>`, for its `n`-th effect for the same record."""
        if n < 0:
            raise ValueError("an occurrence number is not negative")

        def call(*args: P.args, **kwargs: P.kwargs) -> R:
            return cast(R, self._step(self.key(n), *args, **kwargs))

        return call

    def key(self, n: int | None = None) -> IdempotencyKey:
        """The key this step gets in the running workflow."""
        record = _record.get()
        if record is None:
            raise RuntimeError(
                f"external step {self.spec.name!r} runs only inside a workflow registered "
                "with store.workflow and started for a record"
            )
        return IdempotencyKey(record=record, step=self.spec.name, n=n)


def external_step[**P, R](
    name: str, *, effect: str, kill_points: Sequence[str] | None = None
) -> Callable[[Callable[Concatenate[IdempotencyKey, P], R]], ExternalStep[P, R]]:
    """Register the decorated function as the external step `name`.

    The function takes the `IdempotencyKey` first and must hand it to its
    target; the caller passes only the other arguments. `effect` says what
    the step changes outside the database. `kill_points` defaults to
    `before:<name>` and `after:<name>`; a step that declares others reaches
    them with `kill_point`. Asynchronous functions are supported.
    """
    if not name.strip() or ":" in name:
        raise ValueError(f"external step name {name!r} is empty or contains ':'")
    if not effect.strip():
        raise ValueError(f"external step {name!r} declares no effect")
    points = tuple(kill_points) if kill_points is not None else default_kill_points(name)
    before, after = default_kill_points(name)

    def register(func: Callable[Concatenate[IdempotencyKey, P], R]) -> ExternalStep[P, R]:
        if name in _registry.steps:
            raise ValueError(f"external step {name!r} is already registered")
        positional = [
            p
            for p in inspect.signature(func).parameters.values()
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
        if not positional:
            raise TypeError(f"external step {name!r} takes no idempotency key")
        call = cast(Callable[..., object], func)
        run: Callable[..., object]
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def run_async(*args: object, **kwargs: object) -> object:
                kill_point(before)
                result = await cast(Awaitable[object], call(*args, **kwargs))
                kill_point(after)
                return result

            run = run_async
        else:

            @functools.wraps(func)
            def run_sync(*args: object, **kwargs: object) -> object:
                kill_point(before)
                result = call(*args, **kwargs)
                kill_point(after)
                return result

            run = run_sync
        spec = ExternalStepSpec(
            name=name, module=func.__module__, effect=effect, kill_points=points
        )
        _registry.steps[name] = spec
        return ExternalStep[P, R](spec, DBOS.step(name=name)(run))

    return register


def registered_external_steps() -> Mapping[str, ExternalStepSpec]:
    """Every external step registered through `external_step`, by name."""
    return MappingProxyType(_registry.steps)


def bind_record[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """Run `func` with its first input as the causing record its external steps are keyed by.

    `workflow` wraps every registered workflow with this before DBOS sees it,
    so recovery and forks, which call the workflow with its recorded inputs,
    give its steps the same keys.
    """
    if inspect.iscoroutinefunction(func):
        call_async = cast(Callable[..., Awaitable[object]], func)

        @functools.wraps(func)
        async def bound_async(*args: object, **kwargs: object) -> object:
            with _causing(args):
                return await call_async(*args, **kwargs)

        return cast(Callable[P, R], bound_async)

    @functools.wraps(func)
    def bound(*args: P.args, **kwargs: P.kwargs) -> R:
        with _causing(args):
            return func(*args, **kwargs)

    return bound


@contextmanager
def _causing(args: Sequence[object]) -> Generator[None]:
    record = args[0] if args and isinstance(args[0], str) and args[0].strip() else None
    token = _record.set(record)
    try:
        yield
    finally:
        _record.reset(token)


def kill_point(name: str) -> None:
    """Kill the process at `name`, once, when `GRINDSTONE_KILL_AT` names it.

    The kill is abrupt: no cleanup, no commit, no checkpoint (SIGKILL; on
    Windows, which has no SIGKILL, an immediate exit). The marker file is
    written first, so the restarted process runs through the same point.
    """
    if os.environ.get(KILL_AT_ENV) != name:
        return
    marker_path = os.environ.get(KILL_MARKER_ENV)
    if not marker_path:
        raise RuntimeError(f"{KILL_AT_ENV} is set without {KILL_MARKER_ENV}")
    marker = Path(marker_path)
    if marker.exists():
        return
    marker.write_text(name, encoding="utf-8")
    if sys.platform != "win32":
        os.kill(os.getpid(), signal.SIGKILL)
    os._exit(137)
