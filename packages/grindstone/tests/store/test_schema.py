"""Per-module migrations: discovery order and the start-up runner (REQ-0202)."""

from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from grindstone.store import (
    KERNEL_MODULES,
    StoreError,
    discover,
    kernel_migration_sources,
    migrate,
)


def _module(root: Path, name: str, files: dict[str, str]) -> Path:
    directory = root / name / "migrations"
    directory.mkdir(parents=True)
    for file_name, sql in files.items():
        (directory / file_name).write_text(sql)
    return directory


def _fixture_sources(root: Path) -> dict[str, Path]:
    """Three modules, given out of module-map order on purpose."""
    return {
        "intent": _module(
            root,
            "intent",
            {
                "0002_titles.sql": "ALTER TABLE intent.items ADD COLUMN title text;",
                "0001_items.sql": "CREATE SCHEMA intent;\nCREATE TABLE intent.items (id text);",
            },
        ),
        "platform": _module(
            root,
            "platform",
            {"0001_names.sql": "CREATE SCHEMA platform;\nCREATE TABLE platform.names (n text);"},
        ),
        "store": Path(str(kernel_migration_sources()["store"])),
    }


def test_kernel_sources_follow_the_module_map() -> None:
    sources = kernel_migration_sources()
    assert next(iter(sources)) == "store"
    assert list(sources) == [m for m in KERNEL_MODULES if m in sources]
    assert discover(sources)[0].name == "0001_ledger.sql"


def test_discovery_orders_by_module_map_then_number(tmp_path: Path) -> None:
    found = [(m.module, m.number) for m in discover(_fixture_sources(tmp_path))]
    assert found == [("store", 1), ("platform", 1), ("intent", 1), ("intent", 2)]


@pytest.mark.parametrize(
    ("module", "files"),
    [
        ("intent", {"1_items.sql": "SELECT 1;"}),
        ("intent", {"0001_a.sql": "SELECT 1;", "0001_b.sql": "SELECT 1;"}),
        ("sdlc", {"0001_items.sql": "SELECT 1;"}),
    ],
    ids=["unnumbered", "duplicate-number", "not-a-kernel-module"],
)
def test_discovery_refuses_malformed_sources(
    tmp_path: Path, module: str, files: dict[str, str]
) -> None:
    with pytest.raises(StoreError) as caught:
        discover({module: _module(tmp_path, module, files)})
    assert caught.value.code == "migration_failed"


@pytest.mark.integration
def test_migrations_apply_once_in_order(engine: Engine, tmp_path: Path) -> None:
    """AC-0202-1."""
    sources = _fixture_sources(tmp_path)

    applied = migrate(engine, sources)
    expected = [("store", 1), ("platform", 1), ("intent", 1), ("intent", 2)]
    assert [(m.module, m.number) for m in applied] == expected
    with engine.connect() as conn:
        ledger = conn.execute(
            text("SELECT module, number FROM store.migrations ORDER BY applied_at, module")
        ).all()
        assert [tuple(row) for row in ledger] == expected
        assert conn.execute(text("SELECT count(*) FROM intent.items")).scalar_one() == 0

    assert migrate(engine, sources) == []

    (sources["intent"] / "0001_items.sql").write_text(
        "CREATE SCHEMA intent;\nCREATE TABLE intent.items (id text PRIMARY KEY);"
    )
    with pytest.raises(StoreError) as caught:
        migrate(engine, sources)
    assert caught.value.code == "migration_failed"
    assert "intent/0001_items.sql" in str(caught.value)


@pytest.mark.integration
def test_failed_migration_leaves_nothing_behind(engine: Engine, tmp_path: Path) -> None:
    sources = _fixture_sources(tmp_path)
    (sources["intent"] / "0002_titles.sql").write_text(
        "ALTER TABLE intent.items ADD COLUMN title text;\nSELECT * FROM intent.missing;"
    )
    with pytest.raises(StoreError) as caught:
        migrate(engine, sources)
    assert caught.value.code == "migration_failed"
    with engine.connect() as conn:
        ledger = conn.execute(text("SELECT module, number FROM store.migrations")).all()
        assert ("intent", 2) not in {tuple(row) for row in ledger}
        columns = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns"
                " WHERE table_schema = 'intent' AND table_name = 'items'"
            )
        ).scalars()
        assert list(columns) == ["id"]
