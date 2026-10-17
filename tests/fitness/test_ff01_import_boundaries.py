"""FF-01: import boundaries follow the module map, I-18 and the SDK rule."""

import shutil
from pathlib import Path

import pytest
from scripts.ff.module_map import render

from tests.fitness.helpers import FIXTURES, REPO, copy_sources, lint_imports


def test_committed_contracts_match_the_module_map() -> None:
    assert (REPO / ".importlinter").read_text() == render(), (
        "regenerate with: python -m scripts.ff.module_map > .importlinter"
    )


def test_repository_keeps_every_contract(tmp_path: Path) -> None:
    result = lint_imports(copy_sources(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr


def test_kernel_importing_a_factory_fails_the_build(tmp_path: Path) -> None:
    root = copy_sources(tmp_path)
    shutil.copy(
        FIXTURES / "kernel_imports_factory" / "_ff_probe.py", root / "grindstone" / "intent"
    )
    result = lint_imports(root)
    assert result.returncode != 0
    assert "I-18: the kernel never imports a factory BROKEN" in result.stdout


@pytest.mark.parametrize(
    ("package_dir", "statement", "contract"),
    [
        ("grindstone/store", "import grindstone.work", "grindstone.store imports only"),
        ("grindstone/change", "import grindstone.stations", "grindstone.change imports only"),
        ("grindstone/intent", "import grindstone.sdk", "grindstone.intent imports only"),
        ("grindstone_sdlc", "import grindstone.store", "Factories import only grindstone.sdk"),
        ("grindstone_sdlc", "import grindstone_notes", "Factories never import each other"),
        ("grindstone_runner", "import grindstone.contracts", "The runner shares no code"),
    ],
)
def test_forbidden_imports_fail_the_build(
    tmp_path: Path, package_dir: str, statement: str, contract: str
) -> None:
    root = copy_sources(tmp_path)
    (root / package_dir / "_ff_probe.py").write_text(f"{statement}  # noqa: F401\n")
    result = lint_imports(root)
    assert result.returncode != 0
    broken = [line for line in result.stdout.splitlines() if line.endswith("BROKEN")]
    assert any(contract in line for line in broken), result.stdout
