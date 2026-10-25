"""The crash harness fixture, on the shared database fixtures."""

from pathlib import Path

import pytest
from packages.grindstone.tests.conftest import database_url

from tests.crash.harness import CrashHarness

__all__ = ["crash_harness", "database_url"]


@pytest.fixture
def crash_harness(database_url: str, tmp_path: Path) -> CrashHarness:
    """A harness for one fresh test database and one fake target."""
    return CrashHarness(database_url, tmp_path)
