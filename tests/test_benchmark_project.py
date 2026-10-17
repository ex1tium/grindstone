"""The benchmark project (M0-04): 20,000 items, no dangling references, reproducible."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from scripts.benchmark import IMPACT_TARGET, TOTAL, generate, write

# Changing the generator changes this digest: update it in the same commit, deliberately.
GOLDEN_SHA256 = "21c25ec16f1cf9551f89c2812b79f702d287a20642bd66b62b722fa86e0c1379"


def test_benchmark_project_is_complete_reproducible_and_probed(tmp_path: Path) -> None:
    manifest = write(generate(), tmp_path, 20_000)
    assert manifest["items"] == TOTAL
    assert manifest["dangling_references"] == 0
    probe = cast("dict[str, int]", manifest["impact_probe"])
    assert abs(probe["reaches"] - IMPACT_TARGET) <= 25  # FF-14's "a change touching 500 items"
    assert manifest["sha256"] == GOLDEN_SHA256
    assert json.loads((tmp_path / "manifest.json").read_text())["sha256"] == GOLDEN_SHA256


def test_a_different_seed_gives_a_different_project(tmp_path: Path) -> None:
    manifest = write(generate(7), tmp_path, 7)
    assert manifest["items"] == TOTAL
    assert manifest["dangling_references"] == 0
    assert manifest["sha256"] != GOLDEN_SHA256
