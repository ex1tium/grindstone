"""Fixtures for every module's integration tests.

They need PostgreSQL: `GRINDSTONE_TEST_DATABASE_URL` names a server and a role
that may create databases (CI runs a `postgres` service). Each test gets a
fresh database, dropped afterwards. Without the variable the tests are skipped.
"""

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from dbos import DBOS
from psycopg import sql
from sqlalchemy import Engine, make_url

from grindstone.platform.configuration import CONFIG_ENV
from grindstone.store import Database, close_database, create_engine, open_database

TEST_DATABASE_ENV = "GRINDSTONE_TEST_DATABASE_URL"


def _libpq_url(url: str) -> str:
    """The same URL in the form psycopg accepts."""
    return make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)


@pytest.fixture(autouse=True)
def instance_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty instance file for start-up, which refuses to run without one (SPEC-05).

    A test that needs another file sets `GRINDSTONE_CONFIG` itself.
    """
    path = tmp_path / "grindstone.toml"
    path.write_text("", encoding="utf-8")
    monkeypatch.setenv(CONFIG_ENV, str(path))
    return path


@pytest.fixture
def database_url() -> Iterator[str]:
    """A fresh, empty database on the test server, as a SQLAlchemy URL string."""
    server = os.environ.get(TEST_DATABASE_ENV)
    if not server:
        pytest.skip(f"{TEST_DATABASE_ENV} is not set; integration tests need PostgreSQL")
    name = f"gs_test_{uuid.uuid4().hex[:16]}"
    with psycopg.connect(_libpq_url(server), autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        yield (
            make_url(server)
            .set(drivername="postgresql+psycopg", database=name)
            .render_as_string(hide_password=False)
        )
    finally:
        with psycopg.connect(_libpq_url(server), autocommit=True) as conn:
            conn.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
            )


@pytest.fixture
def engine(database_url: str) -> Iterator[Engine]:
    """An engine of the test's own, for setting up and inspecting the database."""
    test_engine = create_engine(database_url)
    try:
        yield test_engine
    finally:
        test_engine.dispose()


@pytest.fixture
def store(database_url: str) -> Iterator[Database]:
    """The store opened on the fresh database, as start-up opens it.

    DBOS is configured first, not launched, as `start_runtime` does: the
    datasource registers with the current DBOS instance, which must not be one
    an earlier test launched and destroyed.
    """
    DBOS(
        config={
            "name": "grindstone-test",
            "system_database_url": database_url,
            "dbos_system_schema": "dbos",
            "application_version": "test",
        }
    )
    try:
        database = open_database(database_url)
        try:
            yield database
        finally:
            close_database()
    finally:
        DBOS.destroy()


@pytest.fixture
def dbos_store(store: Database) -> Iterator[Database]:
    """The store with DBOS launched on the same database, system tables in `dbos`."""
    DBOS.launch()
    try:
        yield store
    finally:
        DBOS.destroy()
