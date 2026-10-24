"""Per-module schema migrations, applied at start-up before DBOS launches.

Each kernel module owns one schema named after it (ADR-02) and ships its
changes as numbered SQL files, `migrations/NNNN_<slug>.sql`, inside its
package. The runner applies the pending ones in module-map order and, within a
module, by number; each file runs in its own transaction together with its
ledger row in `store.migrations`, so a crash leaves it applied or not at all.
Migrations are append-only: an applied file whose hash later changes, or that
has disappeared, fails start-up with `migration_failed` (SPEC-02, REQ-0202,
DEC-0203).

The store does not import the other modules (FF-01); it reads their migration
files as package data.
"""

import hashlib
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable

import psycopg
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError

from grindstone.store.errors import StoreError

_log = logging.getLogger(__name__)

# The module map's kernel layers, lowest first: a module's migrations may rely
# on those of the modules before it, never after.
KERNEL_MODULES: tuple[str, ...] = (
    "store",
    "platform",
    "intent",
    "evidence",
    "decisions",
    "memory",
    "stations",
    "change",
    "work",
    "delivery",
    "surface",
)

LOCK_TIMEOUT = "10s"
_FILE_NAME = re.compile(r"^(\d{4})_([a-z0-9][a-z0-9_]*)\.sql$")
# One runner at a time per database, whichever process starts first.
_RUNNER_LOCK = "SELECT pg_advisory_lock(hashtextextended('grindstone.store.migrations', 0))"
_RUNNER_UNLOCK = "SELECT pg_advisory_unlock(hashtextextended('grindstone.store.migrations', 0))"

type MigrationSources = Mapping[str, Traversable]


@dataclass(frozen=True, slots=True)
class Migration:
    """One migration file of one module."""

    module: str
    number: int
    name: str
    sql: str
    sha256: str


def kernel_migration_sources() -> dict[str, Traversable]:
    """Each kernel module's `migrations/` directory that exists, in module-map order."""
    root = files("grindstone")
    sources: dict[str, Traversable] = {}
    for module in KERNEL_MODULES:
        directory = root / module / "migrations"
        if directory.is_dir():
            sources[module] = directory
    return sources


def discover(sources: MigrationSources) -> list[Migration]:
    """Every migration in `sources`, in module-map order, then by number."""
    unknown = sorted(set(sources) - set(KERNEL_MODULES))
    if unknown:
        raise StoreError("migration_failed", f"not kernel modules: {', '.join(unknown)}")
    found: list[Migration] = []
    for module in KERNEL_MODULES:
        if module not in sources:
            continue
        numbered: dict[int, Migration] = {}
        for entry in sources[module].iterdir():
            if not entry.name.endswith(".sql"):
                continue
            match = _FILE_NAME.match(entry.name)
            if match is None:
                raise StoreError(
                    "migration_failed", f"{module}/{entry.name} is not named NNNN_<slug>.sql"
                )
            number = int(match.group(1))
            if number in numbered:
                raise StoreError(
                    "migration_failed",
                    f"{module} has two migrations numbered {number:04d}: "
                    f"{numbered[number].name} and {entry.name}",
                )
            content = entry.read_bytes()
            numbered[number] = Migration(
                module=module,
                number=number,
                name=entry.name,
                sql=content.decode("utf-8"),
                sha256=hashlib.sha256(content).hexdigest(),
            )
        found.extend(numbered[n] for n in sorted(numbered))
    return found


def migrate(engine: Engine, sources: MigrationSources | None = None) -> list[Migration]:
    """Apply every pending migration and return those applied, in order.

    `sources` defaults to the kernel modules' own migration directories.
    Raises `StoreError("migration_failed")` when an applied file changed or a
    file fails, and `StoreError("database_unavailable")` when the database
    cannot be reached.
    """
    migrations = discover(kernel_migration_sources() if sources is None else sources)
    try:
        with engine.connect() as conn:
            conn.execute(text(_RUNNER_LOCK))
            conn.commit()
            try:
                return _apply_pending(conn, migrations)
            finally:
                # A broken connection has already lost its session lock.
                if not conn.invalidated:
                    conn.rollback()
                    conn.execute(text(_RUNNER_UNLOCK))
                    conn.commit()
    except DBAPIError as exc:
        # The class name is enough to diagnose; the message may carry connection details.
        raise StoreError("database_unavailable", type(exc.orig).__name__) from None


def _apply_pending(conn: Connection, migrations: list[Migration]) -> list[Migration]:
    applied = _ledger(conn)
    conn.commit()
    on_disk = {(m.module, m.number) for m in migrations}
    vanished = sorted(key for key in applied if key[0] in KERNEL_MODULES and key not in on_disk)
    if vanished:
        module, number = vanished[0]
        raise StoreError(
            "migration_failed", f"{module} migration {number:04d} was applied but is missing"
        )
    done: list[Migration] = []
    for migration in migrations:
        recorded = applied.get((migration.module, migration.number))
        if recorded is not None:
            if recorded != migration.sha256:
                raise StoreError(
                    "migration_failed",
                    f"{migration.module}/{migration.name} changed after it was applied; "
                    "migrations are append-only",
                )
            continue
        _apply(conn, migration)
        done.append(migration)
    return done


def _ledger(conn: Connection) -> dict[tuple[str, int], str]:
    """What `store.migrations` records, or nothing on a fresh database."""
    exists = conn.execute(text("SELECT to_regclass('store.migrations') IS NOT NULL")).scalar_one()
    if not exists:
        return {}
    rows = conn.execute(text("SELECT module, number, sha256 FROM store.migrations"))
    return {(row.module, row.number): row.sha256 for row in rows}


def _apply(conn: Connection, migration: Migration) -> None:
    """Run one file and record it, in one transaction."""
    label = f"{migration.module}/{migration.name}"
    try:
        with conn.begin():
            conn.execute(text(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'"))
            # A file holds several statements; psycopg runs them in one call
            # when no parameters are bound.
            conn.connection.cursor().execute(migration.sql)
            conn.execute(
                text(
                    "INSERT INTO store.migrations (module, number, sha256)"
                    " VALUES (:module, :number, :sha256)"
                ),
                {
                    "module": migration.module,
                    "number": migration.number,
                    "sha256": migration.sha256,
                },
            )
    except (DBAPIError, psycopg.Error) as exc:
        # The file runs on the driver's cursor, so its errors arrive unwrapped.
        orig = exc.orig if isinstance(exc, DBAPIError) else exc
        sqlstate = getattr(orig, "sqlstate", None)
        if sqlstate is None or str(sqlstate).startswith("08"):
            raise StoreError("database_unavailable", type(orig).__name__) from None
        raise StoreError(
            "migration_failed", f"{label} failed: {type(orig).__name__} ({sqlstate})"
        ) from exc
    _log.info("applied migration %s", label)
