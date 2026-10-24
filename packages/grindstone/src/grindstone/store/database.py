"""Database access: connection settings, the process's engine, and a liveness probe.

One SQLAlchemy Core engine over psycopg 3 serves the whole process, and the
DBOS datasource that runs workflow transactions shares it, so there is one
pool and one transaction API (SPEC-02, DEC-0201). `open_database` is the
start-up step that applies pending migrations and creates the datasource; it
runs before DBOS launches, which requires datasources to exist first.

M0 bootstrap: settings come from environment variables and a mounted secret
file. SPEC-03 replaces this with the instance configuration (`grindstone.toml`).
"""

import os
from dataclasses import dataclass
from pathlib import Path

import psycopg
import sqlalchemy
from dbos import SQLAlchemyDatasource
from psycopg.conninfo import make_conninfo
from sqlalchemy import URL, Engine

from grindstone.contracts import DependencyHealth, HealthStatus
from grindstone.store.schema import MigrationSources, migrate

# DBOS keeps each datasource transaction's checkpoint in this schema, beside
# the store's own tables (SPEC-02, REQ-0215 exempts it).
DATASOURCE_SCHEMA = "store"


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    """Where the control plane's PostgreSQL is and how to log in."""

    host: str
    port: int
    dbname: str
    user: str
    password_file: Path | None

    @classmethod
    def from_env(cls) -> DatabaseSettings:
        """Read `GRINDSTONE_DB_*` variables; the password is read from a file, never the env."""
        password_file = os.environ.get("GRINDSTONE_DB_PASSWORD_FILE")
        return cls(
            host=os.environ.get("GRINDSTONE_DB_HOST", "localhost"),
            port=int(os.environ.get("GRINDSTONE_DB_PORT", "5432")),
            dbname=os.environ.get("GRINDSTONE_DB_NAME", "grindstone"),
            user=os.environ.get("GRINDSTONE_DB_USER", "grindstone"),
            password_file=Path(password_file) if password_file else None,
        )

    def conninfo(self, *, connect_timeout: int = 3) -> str:
        """Build a libpq connection string; the password never appears in logs or errors."""
        password = self.password_file.read_text().strip() if self.password_file else None
        return make_conninfo(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=password,
            connect_timeout=connect_timeout,
            application_name="grindstone",
        )

    def url(self) -> URL:
        """The SQLAlchemy URL for the engine; render it only with the password hidden."""
        password = self.password_file.read_text().strip() if self.password_file else None
        return URL.create(
            "postgresql+psycopg",
            username=self.user,
            password=password,
            host=self.host,
            port=self.port,
            database=self.dbname,
            query={"application_name": "grindstone"},
        )


@dataclass(frozen=True, slots=True)
class Database:
    """The process's engine and the DBOS datasource built on it."""

    engine: Engine
    datasource: SQLAlchemyDatasource


class _Active:
    """Holds the database `open_database` set up for this process."""

    database: Database | None = None


_active = _Active()


def create_engine(url: URL | str) -> Engine:
    """One pooled engine on psycopg 3, whatever driver the URL names."""
    return sqlalchemy.create_engine(
        sqlalchemy.make_url(url).set(drivername="postgresql+psycopg"), pool_pre_ping=True
    )


def open_database(url: URL | str, *, migrations: MigrationSources | None = None) -> Database:
    """Start the store: apply pending migrations, then create the DBOS datasource.

    Runs once per process, before `DBOS.launch()`. `migrations` defaults to
    the kernel modules' own files; tests pass their own.
    """
    if _active.database is not None:
        raise RuntimeError("the store's database is already open in this process")
    engine = create_engine(url)
    try:
        migrate(engine, migrations)
        datasource = SQLAlchemyDatasource.create(
            engine.url.render_as_string(hide_password=True),
            engine=engine,
            schema=DATASOURCE_SCHEMA,
        )
    except BaseException:
        engine.dispose()
        raise
    _active.database = Database(engine=engine, datasource=datasource)
    return _active.database


def close_database() -> None:
    """Release the process's connections; `open_database` may run again afterwards."""
    if _active.database is not None:
        _active.database.engine.dispose()
        _active.database = None


def current_database() -> Database:
    """The database `open_database` set up for this process."""
    if _active.database is None:
        raise RuntimeError("the store's database is not open: call open_database() at start-up")
    return _active.database


def ping(settings: DatabaseSettings) -> DependencyHealth:
    """Report whether the database accepts a connection and answers a trivial query."""
    try:
        with psycopg.connect(settings.conninfo()) as conn:
            conn.execute("SELECT 1")
    except (psycopg.Error, OSError) as exc:
        # The class name is enough to diagnose; the message may carry connection details.
        return DependencyHealth(
            name="postgres", status=HealthStatus.DOWN, detail=type(exc).__name__
        )
    return DependencyHealth(name="postgres", status=HealthStatus.OK)
