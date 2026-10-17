import threading
from pathlib import Path

from grindstone_runner.__main__ import HEARTBEAT_MAX_AGE_S, healthcheck, serve


def test_serve_writes_heartbeat_and_stops(tmp_path: Path) -> None:
    heartbeat = tmp_path / "hb"
    stop = threading.Event()
    thread = threading.Thread(target=serve, args=(tmp_path, heartbeat, stop))
    thread.start()
    for _ in range(100):
        if heartbeat.exists():
            break
        threading.Event().wait(0.01)
    stop.set()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert healthcheck(heartbeat) == 0


def test_serve_refuses_missing_runs_dir(tmp_path: Path) -> None:
    assert serve(tmp_path / "missing", tmp_path / "hb", threading.Event()) == 2


def test_healthcheck_rejects_stale_missing_and_garbage(tmp_path: Path) -> None:
    heartbeat = tmp_path / "hb"
    assert healthcheck(heartbeat) == 1
    heartbeat.write_text("garbage")
    assert healthcheck(heartbeat) == 1
    heartbeat.write_text("1000.0")
    assert healthcheck(heartbeat, now=1000.0 + HEARTBEAT_MAX_AGE_S + 1) == 1
    assert healthcheck(heartbeat, now=1000.0 + 1) == 0
