"""The unit of work: one SERIALIZABLE transaction, retried on serialization failure.

Two entry points give the caller the same `Uow` (SPEC-02, REQ-0203):

- Inside a workflow, a database-only step is a `@transaction` function. It
  runs as a DBOS datasource transaction, so its writes and the step's
  checkpoint commit together or not at all, and a step that committed never
  runs again (DEC-0202). DBOS retries it on serialization failure.
- Outside workflows (REST reads, start-up, the loader), `unit_of_work(work)`
  runs `work` in its own transaction and re-runs it, up to `MAX_RETRIES`
  times with jittered backoff, when Postgres reports a serialization failure.
  It takes a function rather than a `with` block because a retry must run the
  caller's statements again, which a `with` body cannot.

Modules write SQL text, schema-qualified, through `Uow`; they never see a raw
connection, and nothing uses the ORM.
"""

import functools
import logging
import random
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Concatenate

from sqlalchemy import Connection, RowMapping, text
from sqlalchemy.exc import DBAPIError

from grindstone.store.database import current_database
from grindstone.store.errors import StoreError

_log = logging.getLogger(__name__)

MAX_RETRIES = 5
_BACKOFF_BASE_SECONDS = 0.01
_BACKOFF_CAP_SECONDS = 0.5
# 40001 serialization_failure, 40P01 deadlock_detected: the transaction can be re-run as is.
_RETRYABLE_SQLSTATES = frozenset({"40001", "40P01"})

type Params = Mapping[str, Any]
type Row = RowMapping


class Uow:
    """One open transaction, seen through the statements a module may run."""

    __slots__ = ("_conn",)

    def __init__(self, connection: Connection) -> None:
        self._conn = connection

    def execute(self, sql: str, params: Params | None = None) -> int:
        """Run a statement and return the number of rows it affected."""
        return self._conn.execute(text(sql), dict(params or {})).rowcount

    def fetch_one(self, sql: str, params: Params | None = None) -> Row | None:
        """The first row of a query, or None when it returns none."""
        return self._conn.execute(text(sql), dict(params or {})).mappings().first()

    def fetch_all(self, sql: str, params: Params | None = None) -> Sequence[Row]:
        """Every row of a query."""
        return self._conn.execute(text(sql), dict(params or {})).mappings().all()

    def lock(self, key: str) -> None:
        """Take a transaction-scoped advisory lock on `key`, released at commit or rollback."""
        self._conn.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": key}
        )


def unit_of_work[R](work: Callable[[Uow], R]) -> R:
    """Run `work` in one SERIALIZABLE transaction and return its result.

    `work` may run more than once, so it must not have effects outside the
    database. Raises `StoreError("database_unavailable")` when Postgres cannot
    be reached, and the last serialization failure once the retries run out.
    """
    engine = current_database().engine
    attempt = 0
    while True:
        try:
            with engine.connect() as conn:
                conn.execution_options(isolation_level="SERIALIZABLE")
                with conn.begin():
                    return work(Uow(conn))
        except DBAPIError as exc:
            if _sqlstate(exc) in _RETRYABLE_SQLSTATES and attempt < MAX_RETRIES:
                attempt += 1
                _log.warning("unit of work retried after serialization failure (%d)", attempt)
                time.sleep(_backoff(attempt))
                continue
            if _is_unavailable(exc):
                # The class name is enough to diagnose; the message may carry connection details.
                raise StoreError("database_unavailable", type(exc.orig).__name__) from None
            raise


def transaction[**P, R](func: Callable[Concatenate[Uow, P], R]) -> Callable[P, R]:
    """Make `func(uow, ...)` a DBOS datasource transaction at SERIALIZABLE.

    Called inside a workflow, it is a step whose writes commit with its
    checkpoint; called outside one, it is a plain retried transaction. The
    caller omits `uow`.
    """
    name = func.__qualname__

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        datasource = current_database().datasource

        def body(*inner_args: P.args, **inner_kwargs: P.kwargs) -> R:
            return func(Uow(datasource.sql_session().connection()), *inner_args, **inner_kwargs)

        step = datasource.transaction(name=name, isolation_level="SERIALIZABLE")(body)
        return step(*args, **kwargs)

    return wrapper


def _sqlstate(exc: DBAPIError) -> str | None:
    sqlstate = getattr(exc.orig, "sqlstate", None)
    return sqlstate if isinstance(sqlstate, str) else None


def _is_unavailable(exc: DBAPIError) -> bool:
    """A lost or refused connection, as opposed to an error in the statement."""
    sqlstate = _sqlstate(exc)
    return exc.connection_invalidated or sqlstate is None or sqlstate.startswith(("08", "57P"))


def _backoff(attempt: int) -> float:
    """Full jitter: a random wait up to an exponentially growing, capped ceiling."""
    ceiling = min(_BACKOFF_CAP_SECONDS, _BACKOFF_BASE_SECONDS * 2**attempt)
    return random.uniform(0, ceiling)  # noqa: S311 - jitter, not a secret
