"""A fake external target that finds an earlier effect by its idempotency key.

It lives in a directory outside the database, as a real target lives outside
Grindstone: every call is appended to `calls.jsonl`, and an effect is appended
to `effects.jsonl` only when none with the same key exists yet. The harness
reads both after the control plane has been killed and restarted.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

TARGET_DIR_ENV = "GRINDSTONE_TEST_TARGET_DIR"


@dataclass(frozen=True, slots=True)
class Call:
    """One call of the target: the key it carried and what it asked for."""

    key: str
    payload: str


class FakeTarget:
    """The fake target in `directory`."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> FakeTarget:
        """The target the harness named for this control plane."""
        return cls(Path(os.environ[TARGET_DIR_ENV]))

    def apply(self, key: str, payload: str) -> str:
        """Record the effect for `key` once and return its ID; a repeated key finds it."""
        self._append("calls.jsonl", {"key": key, "payload": payload})
        effects = self.effects()
        if key in effects:
            return effects[key]
        effect_id = f"effect-{len(effects) + 1}"
        self._append("effects.jsonl", {"key": key, "id": effect_id})
        return effect_id

    def calls(self) -> list[Call]:
        """Every call, in order."""
        return [Call(key=r["key"], payload=r["payload"]) for r in self._read("calls.jsonl")]

    def effects(self) -> dict[str, str]:
        """Each recorded effect's ID, by key."""
        return {r["key"]: r["id"] for r in self._read("effects.jsonl")}

    def _append(self, name: str, row: dict[str, str]) -> None:
        # Flushed and synced before returning, so a kill right after keeps it.
        with (self.directory / name).open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def _read(self, name: str) -> list[dict[str, str]]:
        path = self.directory / name
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        return [cast(dict[str, str], json.loads(line)) for line in lines if line]
