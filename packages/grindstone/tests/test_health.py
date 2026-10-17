from pathlib import Path

from fastapi.testclient import TestClient

from grindstone.app import create_app
from grindstone.contracts import DependencyHealth, HealthStatus, ServiceHealth
from grindstone.store import DatabaseSettings


def _unreachable_db(tmp_path: Path) -> DatabaseSettings:
    secret = tmp_path / "pw"
    secret.write_text("not-a-real-password\n")
    # Port 1 on localhost refuses connections immediately.
    return DatabaseSettings(host="127.0.0.1", port=1, dbname="x", user="x", password_file=secret)


def test_healthz_is_ok_without_dependencies(tmp_path: Path) -> None:
    client = TestClient(create_app(_unreachable_db(tmp_path)))
    response = client.get("/healthz")
    assert response.status_code == 200
    assert ServiceHealth.model_validate(response.json()).status is HealthStatus.OK


def test_readyz_reports_database_down_without_leaking_details(tmp_path: Path) -> None:
    client = TestClient(create_app(_unreachable_db(tmp_path)))
    response = client.get("/readyz")
    assert response.status_code == 503
    body = ServiceHealth.model_validate(response.json())
    assert body.status is HealthStatus.DOWN
    (dep,) = body.dependencies
    assert dep.name == "postgres"
    assert dep.status is HealthStatus.DOWN
    assert "not-a-real-password" not in response.text


def test_overall_status_is_the_worst_dependency() -> None:
    ok = DependencyHealth(name="a", status=HealthStatus.OK)
    degraded = DependencyHealth(name="b", status=HealthStatus.DEGRADED)
    down = DependencyHealth(name="c", status=HealthStatus.DOWN)
    assert ServiceHealth.from_dependencies("grindstone", "0", (ok,)).status is HealthStatus.OK
    assert (
        ServiceHealth.from_dependencies("grindstone", "0", (ok, degraded)).status
        is HealthStatus.DEGRADED
    )
    assert (
        ServiceHealth.from_dependencies("grindstone", "0", (degraded, down)).status
        is HealthStatus.DOWN
    )
