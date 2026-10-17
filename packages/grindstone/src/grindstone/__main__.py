"""Run the control plane: `python -m grindstone`."""

import os

import uvicorn

from grindstone.app import create_app


def main() -> None:
    """Serve the control plane on `GRINDSTONE_HTTP_HOST`:`GRINDSTONE_HTTP_PORT`."""
    uvicorn.run(
        create_app(),
        host=os.environ.get("GRINDSTONE_HTTP_HOST", "127.0.0.1"),
        port=int(os.environ.get("GRINDSTONE_HTTP_PORT", "8080")),
        log_config=None,
        server_header=False,
    )


if __name__ == "__main__":
    main()
