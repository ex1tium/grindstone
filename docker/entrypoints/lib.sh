# Shared by the entrypoints (SPEC-05, DEC-0501). POSIX sh, sourced as root.
#
# Compose bind-mounts each secret file with its host owner and mode, so a
# 0600 file owned by the operator is readable here only with DAC_READ_SEARCH.
# The entrypoint refuses any secret that anyone but its owner could read
# (REQ-0514), copies each one into its service user's private tmpfs, and then
# drops every capability its service does not keep.

# gs_fail MESSAGE: report on stderr and stop before the service starts.
gs_fail() {
  printf 'entrypoint: %s\n' "$1" >&2
  exit 1
}

# gs_check_secrets DIR: refuse when a secret in DIR is open to group or others.
# A Windows drive mounted into WSL2 shows every file as 0777, so this also
# fails closed when secrets/ sits on the wrong filesystem (OQ-0501).
gs_check_secrets() {
  [ -d "$1" ] || return 0
  for gs_secret in "$1"/*; do
    [ -e "$gs_secret" ] || continue
    gs_mode=$(stat -L -c '%a' "$gs_secret") || gs_fail "cannot stat secret $gs_secret"
    case "$gs_mode" in
      ?00) ;;
      *) gs_fail "secret $gs_secret has mode $gs_mode; it must be readable only by its owner (chmod 600 on a Linux filesystem)" ;;
    esac
  done
}

# gs_copy_secrets SRC DST USER: copy every secret in SRC into DST as USER.
# DST is a tmpfs Compose mounts owned by USER with mode 0700; root opens each
# original (DAC_READ_SEARCH) and USER writes the copy, 0600, so no capability
# beyond SETUID and SETGID is needed to own it.
gs_copy_secrets() {
  [ -d "$1" ] || return 0
  [ -d "$2" ] || gs_fail "secret copy directory $2 is missing"
  for gs_secret in "$1"/*; do
    [ -e "$gs_secret" ] || continue
    gs_name=$(basename "$gs_secret")
    setpriv --reuid="$3" --regid="$3" --clear-groups \
      sh -c 'umask 077 && cat > "$1"' gs-copy "$2/$gs_name" < "$gs_secret" \
      || gs_fail "cannot copy secret $gs_name into $2"
  done
}
