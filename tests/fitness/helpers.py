import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SOURCE_ROOTS = {
    "grindstone": REPO / "packages" / "grindstone" / "src" / "grindstone",
    "grindstone_sdlc": REPO / "factories" / "sdlc" / "src" / "grindstone_sdlc",
    "grindstone_notes": REPO / "factories" / "notes" / "src" / "grindstone_notes",
    "grindstone_runner": REPO / "runner" / "src" / "grindstone_runner",
}


def copy_sources(dest: Path) -> Path:
    """A scratch copy of every Python package, importable from `dest`."""
    for name, src in SOURCE_ROOTS.items():
        shutil.copytree(src, dest / name, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


def lint_imports(pythonpath: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(pythonpath)}
    lint = Path(sys.executable).with_name("lint-imports")
    return subprocess.run(
        [str(lint), "--config", str(REPO / ".importlinter"), "--no-cache"],
        capture_output=True,
        text=True,
        env=env,
        cwd=pythonpath,
        check=False,
    )
