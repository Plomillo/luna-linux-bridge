#!/usr/bin/env bash
# DIRECTIVA definitive host bootstrap — PUAC-2 aligned, fail-closed, versioned.
# Execute once as root on the registered luna-aux runner.
# Produces the evidence surface the existing puac2-autonomous.yml host job requires.
# Does NOT issue G23 or G24. Those remain independent sequential gates.
set -Eeuo pipefail

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "DIRECTIVA_BOOTSTRAP_START $TS"

if [ "$(id -u)" -ne 0 ]; then
  echo "::error::Must run as root on luna-aux"
  exit 3
fi

CFG=/etc/louksna/remote-bridge/mtls.json
DIR=$(dirname "$CFG")
REPORT_DIR=/var/lib/louksna/reports

mkdir -p "$DIR" "$REPORT_DIR"

# Placeholder config. Real material must be injected via secure channel (never committed).
if [ ! -f "$CFG" ]; then
  cat > "$CFG" <<'EOF'
{
  "schema": "LOUKSNA_MTLS_CONFIG/1.0",
  "status": "BOOTSTRAP_PLACEHOLDER",
  "notes": "Replace with real root-owned mTLS config. Private keys must never enter the repository."
}
EOF
fi
chown root:root "$CFG"
chmod 0640 "$CFG"

if [ -L "$CFG" ]; then
  echo "::error::Config must not be a symlink"
  exit 3
fi

# Service
if systemctl list-unit-files | grep -q louksna-remote-bridge.service; then
  systemctl enable --now louksna-remote-bridge.service || true
else
  echo "WARN: louksna-remote-bridge.service unit not present; install it before expecting host PASS"
fi

# Report templates bound to a placeholder SHA (operator replaces with real candidate SHA)
CANDIDATE_SHA="${CANDIDATE_SHA:-UNKNOWN}"
cat > "$REPORT_DIR/host-tests.report" <<EOF
{
  "schema": "PUAC2_HOST_TEST_REPORT/1.0",
  "status": "PENDING_REAL_EVIDENCE",
  "candidate_commit": "$CANDIDATE_SHA",
  "tests_passed": 0,
  "tests_failed": 0,
  "notes": "Replace with real host test report after real mTLS handshake"
}
EOF
cat > "$REPORT_DIR/rollback.report" <<EOF
{
  "schema": "PUAC2_ROLLBACK_REPORT/1.0",
  "status": "PENDING_REAL_EVIDENCE",
  "candidate_commit": "$CANDIDATE_SHA",
  "rollback_verified": false,
  "notes": "Replace with real rollback verification report"
}
EOF
chown root:root "$REPORT_DIR"/*
chmod 0644 "$REPORT_DIR"/*

echo "DIRECTIVA_BOOTSTRAP_DONE $TS"
echo "Next required (manual on this host):"
echo "  1. Place real client cert/key/CA and point GitHub vars to them"
echo "  2. Replace reports with real PUAC2_*_REPORT/1.0 bound to candidate SHA"
echo "  3. Re-dispatch puac2-autonomous.yml on automation/mtls-evidence-gate-20261013"
