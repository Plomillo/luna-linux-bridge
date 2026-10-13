#!/usr/bin/env bash
set -Eeuo pipefail
if [[ ${1:-} == "--replace" ]]; then
  replace=1
elif [[ $# -eq 0 ]]; then
  replace=0
else
  printf '%s\n' 'Usage: bash configure-github-token.sh [--replace]' >&2
  exit 2
fi
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$ROOT/.env_encoded"
if [[ -e "$TARGET" && "$replace" -ne 1 ]]; then
  printf '%s\n' '.env_encoded exists; use --replace only when deliberately rotating the token.' >&2
  exit 2
fi
printf '%s' 'Fine-grained GitHub token for Plomillo/luna-linux-bridge (hidden input): '
IFS= read -r -s token
printf '\n'
if [[ -z "$token" ]]; then
  printf '%s\n' 'Empty token; no file changed.' >&2
  exit 2
fi
umask 077
tmp="$ROOT/.env.encoded.tmp.$$"
cleanup() {
  rm -f -- "$tmp"
  unset token encoded
}
trap cleanup EXIT
encoded="$(printf '%s' "$token" | base64 | tr -d '\r\n')"
printf 'SECRET_GITHUB_TOKEN=%s\n' "$encoded" > "$tmp"
chmod 600 "$tmp"
mv -f -- "$tmp" "$TARGET"
unset token encoded
printf '%s\n' 'PASS: .env_encoded created with mode 0600; token was not displayed.'
printf '%s\n' 'Verify the token is scoped only to this repository and has Actions: Read and write.'
printf '%s\n' 'Restart Kestra after configuration. Never commit or upload .env_encoded.'
