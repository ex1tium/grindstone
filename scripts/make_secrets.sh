#!/usr/bin/env bash
# `make secrets`: create every secret the Compose deployment needs (SPEC-05, REQ-0513).
#
# Each secret is a file, mode 0600, in a 0700 directory (secrets/, or
# $GRINDSTONE_SECRETS_DIR). A file that exists is never overwritten, so a
# second run changes nothing; rotate a secret by replacing its file and
# restarting the containers that mount it.
#
# - Random keys (32 bytes, base64url): postgres_password, mcp_token_key,
#   host_control_key, host_event_key, session_key.
# - operator_password_hash: the operator password's Argon2id hash only,
#   computed by scripts/hash_password.py, which reads the password itself.
# - github_app_key and claude_oauth_token: copied from paths you give. An
#   empty answer leaves an empty file, which the deployment treats as not
#   configured until you replace it.
#
# On a terminal it asks. Without one (CI), it reads one line for each secret
# it creates, in the order above: the password, then the two paths; at end of
# input the password is random and never shown, and the two files are empty.
# No value is ever printed.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
dir="${GRINDSTONE_SECRETS_DIR:-${root}/secrets}"
umask 077

interactive=false
if [[ -t 0 ]]; then interactive=true; fi

fail() {
  echo "make secrets: $1" >&2
  exit 1
}

mkdir -p "${dir}"
chmod 0700 "${dir}"

# An M0 checkout has secrets/postgres_password at 0644: tighten it, with confirmation.
for existing in "${dir}"/*; do
  [[ -f "${existing}" ]] || continue
  mode="$(stat -c '%a' "${existing}")"
  [[ "${mode}" == ?00 ]] && continue
  if ! ${interactive}; then
    fail "${existing} has mode ${mode}; run make secrets on a terminal to tighten it, or chmod 600 it"
  fi
  read -r -p "${existing} has mode ${mode}; tighten it to 0600? [y/N] " answer
  [[ "${answer}" == [yY]* ]] || fail "${existing} left at ${mode}; the entrypoints refuse it"
  chmod 0600 "${existing}"
  echo "tightened ${existing} to 0600"
done

# create NAME: store standard input as the new secret NAME, unless it exists.
create() {
  local target="${dir}/$1" tmp="${dir}/.$1.tmp.$$"
  cat > "${tmp}"
  chmod 0600 "${tmp}"
  mv "${tmp}" "${target}"
  echo "created ${target}"
}

random_key() {
  head -c 32 /dev/urandom | base64 | tr '+/' '-_' | tr -d '=\n'
}

hash_password() {
  (cd "${root}" && uv run --frozen python -m scripts.hash_password "$@")
}

for name in postgres_password mcp_token_key host_control_key host_event_key session_key; do
  [[ -e "${dir}/${name}" ]] || random_key | create "${name}"
done

if [[ ! -e "${dir}/operator_password_hash" ]]; then
  if ${interactive}; then
    hashed="$(hash_password)"
  else
    password=""
    IFS= read -r password || true
    if [[ -z "${password}" ]]; then
      hashed="$(hash_password --generate)"
      echo "operator password: random and never shown (no terminal); delete ${dir}/operator_password_hash and run make secrets on a terminal to choose one"
    else
      hashed="$(printf '%s\n' "${password}" | hash_password)"
    fi
    unset password
  fi
  [[ "${hashed}" == '$argon2id$'* ]] || fail "hash_password returned no Argon2id hash"
  printf '%s\n' "${hashed}" | create operator_password_hash
  unset hashed
fi

# copy_in NAME QUESTION: copy the file at the path the operator gives into NAME.
copy_in() {
  [[ -e "${dir}/$1" ]] && return 0
  local source=""
  if ${interactive}; then
    read -r -p "$2 (empty to leave it unset): " source
  else
    IFS= read -r source || true
  fi
  if [[ -z "${source}" ]]; then
    create "$1" < /dev/null
    echo "  $1 is empty: replace the file to configure it"
  else
    [[ -f "${source}" && -r "${source}" ]] || fail "cannot read ${source}"
    create "$1" < "${source}"
  fi
}

copy_in github_app_key "Path of the GitHub App's private key (.pem)"
copy_in claude_oauth_token "Path of a file holding the Claude subscription token"
