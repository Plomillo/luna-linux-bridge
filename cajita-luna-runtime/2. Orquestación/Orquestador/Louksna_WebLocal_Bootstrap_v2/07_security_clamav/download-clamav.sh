#!/usr/bin/env bash
set -euo pipefail

VERSION="1.5.4"
TARGET="${1:-rpm}"
case "$TARGET" in
  rpm) FILE="clamav-${VERSION}.linux.x86_64.rpm" ;;
  deb) FILE="clamav-${VERSION}.linux.x86_64.deb" ;;
  source) FILE="clamav-${VERSION}.tar.gz" ;;
  *) echo "Uso: $0 [rpm|deb|source]" >&2; exit 2 ;;
esac
URL="https://github.com/Cisco-Talos/clamav/releases/download/clamav-${VERSION}/${FILE}"
mkdir -p "$(dirname "$0")/payload"
cd "$(dirname "$0")/payload"
command -v curl >/dev/null || { echo "curl es requerido" >&2; exit 1; }
curl -fL --retry 3 -o "$FILE" "$URL"
printf 'Descargado: %s\n' "$FILE"
sha256sum "$FILE"
