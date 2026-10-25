#!/bin/sh
# Agent-host entrypoint (SPEC-05). Runs as root, as the only child of
# Docker's init (`init: true`), holding only DAC_READ_SEARCH, CHOWN, SETUID,
# SETGID and SETPCAP: refuse a secret others could read, copy each into
# /run/gs-host for `gs-host`, then run the host as `gs-host` keeping exactly
# CAP_SETUID and CAP_SETGID, which it needs to start agents as their own
# users (SPK-1). TKT-0502 adds the workspace and session layout here.
set -eu
. "$(dirname "$0")/lib.sh"

secrets_src=${GS_SECRETS_SRC:-/run/secrets}
gs_check_secrets "$secrets_src"
gs_copy_secrets "$secrets_src" "${GS_SECRETS_DST:-/run/gs-host}" gs-host

exec setpriv --reuid=gs-host --regid=gs-host --init-groups \
  --bounding-set=-all,+setuid,+setgid \
  --inh-caps=-all,+setuid,+setgid \
  --ambient-caps=-all,+setuid,+setgid -- "$@"
