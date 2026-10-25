"""`grindstone check`: instance, factory and project configuration validated together (REQ-0312).

It loads the factories exactly as start-up does, validates `grindstone.toml`,
and validates every project configuration: the files given, or else each
project's current version in the database when one is reachable. Every error
is one line, `file:field: rule`.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import URL, make_url
from sqlalchemy.exc import SQLAlchemyError

from grindstone.platform.configuration import (
    check_instance_config,
    latest_project_configs,
    stored_config_file,
    validate_project,
)
from grindstone.platform.core import core_registries
from grindstone.platform.loader import FactorySource, discover, load_factories
from grindstone.store.database import create_engine
from grindstone.store.uow import Uow


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Every error line, and notes on what could not be checked."""

    errors: tuple[str, ...]
    notes: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def check(
    instance_path: Path,
    project_files: Sequence[Path] = (),
    *,
    database: URL | str | None = None,
    sources: Iterable[FactorySource] | None = None,
) -> CheckResult:
    """Validate everything start-up validates, without starting anything."""
    errors: list[str] = []
    notes: list[str] = []
    report = load_factories(core_registries(), discover() if sources is None else sources)
    for name, problems in report.refused.items():
        errors.extend(f"{name}/{p}" for p in problems)
    instance, problems = check_instance_config(instance_path)
    errors.extend(str(p) for p in problems)

    stored: list[tuple[str, str | None]] = []
    for path in project_files:
        try:
            stored.append((str(path), path.read_text(encoding="utf-8")))
        except OSError as exc:
            errors.append(
                f"{path}:-: the file cannot be read: {exc.strerror or type(exc).__name__}"
            )
    if not project_files:
        if database is None:
            notes.append("no project files and no database: project configurations not checked")
        else:
            try:
                stored = _stored_configs(database)
            except SQLAlchemyError as exc:
                # The class name is enough to diagnose; the message may carry connection details.
                reason = type(exc).__name__
                notes.append(f"database unreachable ({reason}): project configurations not checked")
    for file, text in stored:
        if text is None:
            errors.append(f"{file}:-: the project has no configuration")
            continue
        _, problems = validate_project(text, file, report, instance)
        errors.extend(str(p) for p in problems)
    return CheckResult(tuple(errors), tuple(notes))


def _stored_configs(database: URL | str) -> list[tuple[str, str | None]]:
    url = make_url(database).update_query_dict({"connect_timeout": "3"})
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            latest = latest_project_configs(Uow(conn))
    finally:
        engine.dispose()
    return [(stored_config_file(slug, version), toml) for _, slug, version, toml in latest]
