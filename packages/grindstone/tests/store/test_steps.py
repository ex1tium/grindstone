"""The external-step helper without a database: keys, registration and kill points.

The crash-and-resume behaviour (REQ-0204, REQ-0213) is tested in `tests/crash/`.
"""

from pathlib import Path

import pytest

from grindstone.store import (
    KILL_AT_ENV,
    KILL_MARKER_ENV,
    IdempotencyKey,
    external_step,
    kill_point,
    registered_external_steps,
    start,
)


def test_idempotency_key_names_the_record_and_the_step() -> None:
    assert str(IdempotencyKey("run-7", "prompt")) == "run-7:prompt"
    assert str(IdempotencyKey("run-7", "prompt", 3)) == "run-7:prompt:3"


def test_external_step_registration_is_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    # A registry of the test's own, so no step without a crash scenario outlives it.
    monkeypatch.setattr("grindstone.store.steps._registry.steps", {})

    @external_step("test.steps.registered", effect="nothing", kill_points=["after:x"])
    def registered(key: IdempotencyKey) -> str:
        return str(key)

    spec = registered_external_steps()["test.steps.registered"]
    assert spec.effect == "nothing"
    assert spec.kill_points == ("after:x",)
    assert spec.module == __name__
    # Outside a workflow started for a record there is no key to give it.
    with pytest.raises(RuntimeError, match="started for a record"):
        registered()

    def again(key: IdempotencyKey) -> str:
        return str(key)

    with pytest.raises(ValueError, match="already registered"):
        external_step("test.steps.registered", effect="nothing")(again)

    def keyless() -> None:
        return None

    with pytest.raises(TypeError, match="no idempotency key"):
        external_step("test.steps.keyless", effect="nothing")(keyless)  # pyright: ignore[reportArgumentType]
    for bad in ("", "a:b"):
        with pytest.raises(ValueError, match="empty or contains"):
            external_step(bad, effect="nothing")
    with pytest.raises(ValueError, match="declares no effect"):
        external_step("test.steps.no-effect", effect=" ")


def test_start_needs_the_record_as_first_input() -> None:
    def work(record: str) -> str:
        return record

    with pytest.raises(ValueError, match="first input"):
        start("rec-1", work)  # pyright: ignore[reportCallIssue]
    with pytest.raises(ValueError, match="first input"):
        start("rec-1", work, " ")


def test_kill_point_is_inert_unless_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(KILL_AT_ENV, raising=False)
    kill_point("after:anything")
    monkeypatch.setenv(KILL_AT_ENV, "after:other")
    kill_point("after:anything")
    # The point already fired once: the marker lets the restart run through.
    marker = tmp_path / "killed"
    marker.write_text("after:anything")
    monkeypatch.setenv(KILL_AT_ENV, "after:anything")
    monkeypatch.setenv(KILL_MARKER_ENV, str(marker))
    kill_point("after:anything")
    monkeypatch.delenv(KILL_MARKER_ENV)
    with pytest.raises(RuntimeError, match=KILL_MARKER_ENV):
        kill_point("after:anything")
