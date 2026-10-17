#!/bin/bash
# SessionStart hook for Claude Code cloud sessions: makes `make check`,
# `make up` and `make smoke` work in a fresh container. Idempotent; does
# nothing outside cloud sessions (local machines manage their own toolchains).
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
ENV_FILE="${CLAUDE_ENV_FILE:-/dev/null}"
log() { echo "[session-start] $*" >&2; }

# --- Node.js, pinned by .nvmrc and verified against the official checksums ---
NODE_VERSION="$(cat .nvmrc)"
NODE_DIR="/opt/node-v${NODE_VERSION}"
if [ ! -x "${NODE_DIR}/bin/node" ]; then
  log "installing Node.js ${NODE_VERSION}"
  tmp="$(mktemp -d)"
  tarball="node-v${NODE_VERSION}-linux-x64.tar.xz"
  curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/${tarball}" -o "${tmp}/${tarball}"
  curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/SHASUMS256.txt" \
    | grep " ${tarball}\$" | (cd "${tmp}" && sha256sum -c - >&2)
  mkdir -p "${NODE_DIR}"
  tar -xJf "${tmp}/${tarball}" -C "${NODE_DIR}" --strip-components=1
  rm -rf "${tmp}"
fi
export PATH="${NODE_DIR}/bin:${PATH}"
export COREPACK_ENABLE_DOWNLOAD_PROMPT=0
corepack enable --install-directory "${NODE_DIR}/bin" >&2

# uv: use the system trust store (holds the session proxy's CA) without the
# deprecated variable the environment sets.
unset UV_NATIVE_TLS
export UV_SYSTEM_CERTS=1

{
  echo "export PATH=\"${NODE_DIR}/bin:\$PATH\""
  echo "export COREPACK_ENABLE_DOWNLOAD_PROMPT=0"
  echo "unset UV_NATIVE_TLS"
  echo "export UV_SYSTEM_CERTS=1"
} >> "${ENV_FILE}"

# --- Python and Node dependencies (locked) ---
log "syncing Python and Node dependencies"
uv sync --locked >&2
pnpm install --frozen-lockfile >&2

# --- Docker, for make up / make smoke and the spikes ---
if command -v dockerd >/dev/null 2>&1; then
  if [ ! -s /etc/docker/daemon.json ]; then
    # Docker Hub rate-limits anonymous pulls from shared cloud IPs; the mirror
    # serves the same content, so digest pins still hold.
    mkdir -p /etc/docker
    echo '{"registry-mirrors": ["https://mirror.gcr.io"]}' > /etc/docker/daemon.json
  fi
  if ! docker info >/dev/null 2>&1; then
    log "starting dockerd"
    setsid nohup dockerd > /var/log/dockerd.log 2>&1 < /dev/null &
    for _ in $(seq 1 30); do docker info >/dev/null 2>&1 && break; sleep 1; done
  fi
  if docker info >/dev/null 2>&1 && [ -n "${HTTPS_PROXY:-}" ] && [ -s /root/.ccr/ca-bundle.crt ]; then
    # Build containers have no direct egress here: build on the host network
    # through the session proxy, trusting its CA. Session-local, never committed.
    override="${HOME}/.cache/grindstone/compose.cloud.yaml"
    mkdir -p "$(dirname "${override}")"
    cat > "${override}" <<YAML
x-build: &build
  network: host
  args:
    HTTPS_PROXY: ${HTTPS_PROXY}
    https_proxy: ${HTTPS_PROXY}
  secrets: [build_ca]
services:
  grindstone: {build: *build}
  agent-host: {build: *build}
  runner: {build: *build}
secrets:
  build_ca:
    file: /root/.ccr/ca-bundle.crt
YAML
    echo "export COMPOSE_FILE=\"${PWD}/compose.yaml:${override}\"" >> "${ENV_FILE}"
  else
    log "docker unavailable; make up and make smoke will not work in this session"
  fi
fi

log "ready"
