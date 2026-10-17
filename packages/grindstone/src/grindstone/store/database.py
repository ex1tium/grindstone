"""Database connection settings and a liveness probe.

M0 bootstrap: settings come from environment variables and a mounted secret
file. SPEC-02 and SPEC-03 replace this with the instance configuration
(`grindstone.toml`) and the full store.
"""

import os
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg.conninfo import make_conninfo

from grindstone.contracts import DependencyHealth, HealthStatus


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
