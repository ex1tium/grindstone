#!/bin/sh
# Control-plane entrypoint (SPEC-05). Runs as root holding only
# DAC_READ_SEARCH, SETUID, SETGID and SETPCAP: refuse a secret others could
# read, copy each into /run/gs for `grindstone`, then run the service as
# `grindstone` with every capability set, the bounding set included, empty.
set -eu
. "$(dirname "$0")/lib.sh"

secrets_src=${GS_SECRETS_SRC:-/run/secrets}
gs_check_secrets "$secrets_src"
gs_copy_secrets "$secrets_src" "${GS_SECRETS_DST:-/run/gs}" grindstone

exec setpriv --reuid=grindstone --regid=grindstone --init-groups \
  --bounding-set=-all --inh-caps=-all --ambient-caps=-all -- "$@"
