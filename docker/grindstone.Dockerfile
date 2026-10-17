# Control plane: kernel, factories, workflows, APIs, delivery (ADR-01).
# Holds every authority credential, so it runs non-root with a read-only root
# filesystem and never executes work content (I-09).

FROM ghcr.io/astral-sh/uv:0.13.1@sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336 AS uv

FROM python:3.14.8-slim-trixie@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /src
# Workspace metadata first, so dependency layers are cached across source edits.
COPY pyproject.toml uv.lock ./
COPY packages/grindstone/pyproject.toml packages/grindstone/README.md packages/grindstone/
COPY factories/sdlc/pyproject.toml factories/sdlc/
COPY factories/notes/pyproject.toml factories/notes/
COPY runner/pyproject.toml runner/
# Builds behind a TLS-intercepting proxy pass its CA as the optional build
# secret `build_ca`; the standard HTTPS_PROXY build arg is honoured by uv.
RUN --mount=type=secret,id=build_ca,required=false \
    if [ -s /run/secrets/build_ca ]; then export SSL_CERT_FILE=/run/secrets/build_ca; fi; \
    uv sync --locked --no-dev --no-install-workspace --package grindstone-sdlc
COPY packages/grindstone/src packages/grindstone/src
COPY factories/sdlc/src factories/sdlc/src
# The notes fixture is test-only and never ships (Factories tab).
RUN --mount=type=secret,id=build_ca,required=false \
    if [ -s /run/secrets/build_ca ]; then export SSL_CERT_FILE=/run/secrets/build_ca; fi; \
    uv sync --locked --no-dev --no-editable --package grindstone-sdlc

FROM python:3.14.8-slim-trixie@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS runtime
# Shared groups give the volumes the same ownership whichever container
# initialises them first: 10100 workspaces (with agent-host), 10200 runs (with runner).
RUN groupadd --system --gid 10100 gs-workspaces \
 && groupadd --system --gid 10200 gs-runs \
 && groupadd --system --gid 10001 grindstone \
 && useradd --system --uid 10001 --gid grindstone --groups gs-workspaces,gs-runs \
      --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin grindstone \
 && install -d -o grindstone -g grindstone -m 0700 /var/lib/grindstone/blobs /var/lib/grindstone/repos \
 && install -d -o root -g gs-workspaces -m 2770 /var/lib/grindstone/workspaces \
 && install -d -o root -g gs-runs -m 2770 /var/lib/grindstone/runs
COPY --from=build /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GRINDSTONE_HTTP_HOST=0.0.0.0 \
    GRINDSTONE_HTTP_PORT=8080
USER grindstone
EXPOSE 8080
CMD ["python", "-m", "grindstone"]
