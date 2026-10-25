"""The `sdlc` factory loaded through the kernel's loader, on the shared database fixtures."""

import pytest
from factories.sdlc.tests.support import load_sdlc
from packages.grindstone.tests.conftest import database_url, engine, store

from grindstone.platform import Registries
from grindstone.platform.loader import LoadedFactory

__all__ = ["database_url", "engine", "loaded", "store"]


@pytest.fixture
def loaded() -> tuple[Registries, LoadedFactory]:
    """The shipped manifest, loaded with no refusal."""
    registries, report = load_sdlc()
    assert not report.refused, report.lines()
    (factory,) = report.loaded
    return registries, factory
