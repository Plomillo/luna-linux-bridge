#!/usr/bin/env bash
# Scope: create a private, read-only Drive remote for the original semantic
# container. OAuth completion requires the user's Google browser approval.
# Do not copy, upload, echo, or publish OAuth tokens.
set -Eeuo pipefail
umask 077
export PATH="$HOME/.local/bin:$PATH"
fail() { printf 'FAIL_CLOSED: %s\n' "$*" >&2; exit 2; }
[[ "${GITHUB_REPOSITORY:-}" == "Plomillo/luna-linux-bridge" ]] || fail "Wrong repository"
[[ "${GITHUB_REF:-}" == "refs/heads/staging/contenedor-semantico-e826-20260927" ]] || fail "Wrong branch"
command -v rclone >/dev/null || fail "rclone missing"
test -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" || fail "No KDE graphical display"

folder_id="1xvUD6qtPSYgmSFaZMIMpuPnhrm5-Br6X"
remote="louksna_cas_drive"
export RCLONE_CONFIG="$HOME/.config/rclone/rclone.conf"
mkdir -p "$HOME/.config/rclone" "$HOME/.local/state/louksna/oauth"
chmod 0700 "$HOME/.config/rclone" "$HOME/.local/state/louksna/oauth"
if [[ -e "$RCLONE_CONFIG" ]]; then chmod 0600 "$RCLONE_CONFIG"; fi
created=0
auth_log="$HOME/.local/state/louksna/oauth/authorization-$(date -u +%Y%m%dT%H%M%SZ).log"
if rclone listremotes 2>/dev/null | grep -Fxq "${remote}:"; then
  echo "REMOTE_EXISTS_VERIFYING_SCOPE"
else
  # rclone auto-opens Google's authorization page in KDE. The user MUST
  # sign in and approve read-only access. Raw output remains local 0600.
  printf 'OAUTH_BROWSER_REQUESTED_ON_LOUKSNA; TIME_LIMIT_SECONDS=900\n'
  : > "$auth_log"; chmod 0600 "$auth_log"
  if ! timeout 900 rclone config create "$remote" drive \
      scope=drive.readonly root_folder_id="$folder_id" \
      config_is_local=true > "$auth_log" 2>&1; then
    fail "OAuth not completed within 15 minutes or blocked; see local private $auth_log. No token in GitHub logs."
  fi
  created=1
fi

python3 - "$RCLONE_CONFIG" "$remote" "$folder_id" <<'PY'
import configparser, pathlib, sys
path, name, expected_folder = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
if not path.is_file() or path.is_symlink():
    raise SystemExit("FAIL_CLOSED: no secure rclone configuration")
cfg = configparser.ConfigParser(interpolation=None)
cfg.read(path)
if not cfg.has_section(name):
    raise SystemExit("FAIL_CLOSED: remote section missing")
sec = cfg[name]
if sec.get("type") != "drive" or sec.get("scope") != "drive.readonly":
    raise SystemExit("FAIL_CLOSED: remote type/scope unexpected")
if sec.get("root_folder_id") != expected_folder or not sec.get("token"):
    raise SystemExit("FAIL_CLOSED: container root or OAuth token missing")
print("REMOTE_TYPE_SCOPE_ROOT_AND_TOKEN_PRESENCE=PASS")
PY
chmod 0600 "$RCLONE_CONFIG"
# Read-only metadata check; do not print Drive content names into CI logs.
actual="$(rclone ls "${remote}:18_HASH_INDEX/OBJECTS" 2>/dev/null | wc -l)"
[[ "$actual" == "252" ]] || fail "Expected exactly 252 Drive objects in the original container; found $actual"
echo "GOOGLE_DRIVE_CAS_METADATA_COUNT=252"
# Remove raw OAuth session log after validation; keep only the restricted rclone config.\nif [[ -f "$auth_log" ]]; then rm -f -- "$auth_log"; fi\necho "DRIVE_READONLY_AUTHORIZED_AND_SOURCE_SCOPED=PASS"
