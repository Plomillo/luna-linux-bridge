#!/usr/bin/env bash
# Deterministic integration test for the Debian .deb canonicalizer.
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CANON="$SCRIPT_DIR/debian_package_canonicalize.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export SOURCE_DATE_EPOCH=1700000000 TZ=UTC LC_ALL=C
for variant in a b; do
  ROOT="$TMP/root-$variant"
  mkdir -p "$ROOT/DEBIAN" "$ROOT/usr/share/louksna"
  cat > "$ROOT/DEBIAN/control" <<'CONTROL'
Package: louksna-canonicalizer-fixture
Version: 1.0.0
Section: utils
Priority: optional
Architecture: all
Maintainer: Louksna CI <ci@example.invalid>
Description: Synthetic fixture for reproducible Debian package metadata tests
CONTROL
  printf 'payload is immutable\n' > "$ROOT/usr/share/louksna/payload.txt"
  if [ "$variant" = a ]; then EPOCH=1000000000; else EPOCH=1600000000; fi
  find "$ROOT" -exec touch -h -d "@$EPOCH" {} +
  dpkg-deb --build --root-owner-group "$ROOT" "$TMP/raw-$variant.deb" >/dev/null
done
python3 -B -I "$CANON" --package "$TMP/raw-a.deb" --output "$TMP/canonical-a.deb" --source-date-epoch "$SOURCE_DATE_EPOCH"
python3 -B -I "$CANON" --package "$TMP/raw-b.deb" --output "$TMP/canonical-b.deb" --source-date-epoch "$SOURCE_DATE_EPOCH"
A="$(sha256sum "$TMP/canonical-a.deb" | awk '{print $1}')"
B="$(sha256sum "$TMP/canonical-b.deb" | awk '{print $1}')"
test "$A" = "$B" || { echo "FAIL: canonical package hashes differ: $A != $B"; exit 1; }
test "$(dpkg-deb -f "$TMP/canonical-a.deb" Package)" = "louksna-canonicalizer-fixture"
test "$(dpkg-deb -f "$TMP/canonical-a.deb" Version)" = "1.0.0"
mkdir "$TMP/unpacked"
dpkg-deb --extract "$TMP/canonical-a.deb" "$TMP/unpacked"
cmp "$TMP/unpacked/usr/share/louksna/payload.txt" <(printf 'payload is immutable\n')
printf 'PASS canonical_sha256=%s\n' "$A"
