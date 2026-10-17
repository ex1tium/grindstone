#!/usr/bin/env bash
# Create local development secrets under secrets/ if they are missing.
# Production secrets are provisioned by the operator (see docs/m0/operator-setup.md).
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
mkdir -p secrets
if [[ ! -s secrets/postgres_password ]]; then
  head -c 32 /dev/urandom | base64 | tr -d '/+=\n' > secrets/postgres_password
  echo "created secrets/postgres_password"
fi
# Compose bind-mounts file secrets with their host permissions, and the
# services read them as non-root users; the directory stays 0700.
chmod 0700 secrets
chmod 0644 secrets/postgres_password
