"""SPEC-05, TKT-0501: the shipped instance file and the deployment that mounts it."""

from pathlib import Path
from typing import Any, cast

import yaml

from grindstone.platform.configuration import DEFAULT_INSTANCE_CONFIG, read_instance_config

ROOT = Path(__file__).parents[2]
INSTANCE_FILE = ROOT / "deploy" / "grindstone.toml"


def _compose() -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load((ROOT / "compose.yaml").read_text("utf-8")))


def test_instance_file_is_valid_and_names_only_mounted_copies() -> None:
    config = read_instance_config(INSTANCE_FILE)
    grindstone = _compose()["services"]["grindstone"]
    mounted: list[str] = grindstone["secrets"]
    for name, path in config.secrets.items():
        assert path.startswith("/run/gs/"), name
        assert path.removeprefix("/run/gs/") in mounted, name
    assert {"agent-host", "runner"} <= set(config.stations)


def test_instance_file_is_mounted_read_only_in_the_control_plane_only() -> None:
    services: dict[str, dict[str, Any]] = _compose()["services"]
    binds: list[tuple[str, dict[str, Any]]] = [
        (service, cast(dict[str, Any], volume))
        for service, spec in services.items()
        for volume in spec.get("volumes", [])
        if isinstance(volume, dict)
    ]
    assert binds == [
        (
            "grindstone",
            {
                "type": "bind",
                "source": "./deploy/grindstone.toml",
                "target": str(DEFAULT_INSTANCE_CONFIG.as_posix()),
                "read_only": True,
            },
        )
    ]
    assert "GRINDSTONE_CONFIG" not in services["grindstone"].get("environment", {})
