#!/usr/bin/env bash
# DIRECTIVA host bootstrap — versioned, fail-closed, PUAC-2 aligned.
# Run once on the luna-aux runner as root (or with sudo).
# Does NOT claim G23/G24. Only prepares the evidence the existing gates require.
set -Eeuo pipefail

echo "DIRECTIVA_BOOTSTRAP start $(date -u +%Y-%m-%dT%H:%M:%SZ)"

CFG=/etc/louksna/remote-bridge/mtls.json
DIR=$(dirname "$CFG")

if [ "$(id -u)" -ne 0 ]; then
  echo "::error::Must run as root"
  exit 3
fi

mkdir -p "$DIR"
# Minimal placeholder config. Replace with real mTLS material via secrets or secure copy.
# Real certs must come from GitHub Secrets / sealed storage, never committed.
cat > "$CFG" <<'EOF'
{
  "schema": "LOUKSNA_MTLS_CONFIG/1.0",
  "status": "BOOTSTRAP_PLACEHOLDER",
  "notes": "Replace with real root-owned config. Do not commit private keys."
}
EOF
chown root:root "$CFG"
chmod 0640 "$CFG"

if [ -L "$CFG" ]; then
  echo "::error::Config must not be a symlink"
  exit 3
fi

# Service activation (assumes unit file already present on the runner)
if systemctl list-unit-files | grep -q louksna-remote-bridge.service; then
  systemctl enable --now louksna-remote-bridge.service || true
  systemctl is-active --quiet louksna-remote-bridge.service && echo "service active" || echo "service not yet active (unit may need real config)"
else
  echo "service unit not found; operator must install louksna-remote-bridge.service"
fi

echo "DIRECTIVA_BOOTSTRAP done. Next: place real certs/keys/CA and generate host/rollback reports bound to candidate SHA, then re-dispatch puac2-autonomous.yml"
