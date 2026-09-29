#!/bin/bash
set -Eeuo pipefail
umask 077

OWNER="diegoignacionorambuenamiranda"
HOST_EXPECTED="LOUKSNA"
SRC="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
DST="$HOME/.local/lib/louksna/r4-master-part1-part9"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT="$UNIT_DIR/luna-r4-master-part1-part9.service"
STATE="$HOME/.local/state/louksna/r4-master-part1-part9"

hold(){ echo "HOLD:$*" >&2; exit 1; }

[ "$(id -un)" = "$OWNER" ] || hold "OWNER_MISMATCH"
[ "$(hostname)" = "$HOST_EXPECTED" ] || hold "HOST_MISMATCH"
command -v gh >/dev/null 2>&1 || hold "GH_MISSING"
gh auth status >/dev/null 2>&1 || hold "GH_AUTH_REQUIRED"

for f in master_controller.py MASTER_MISSION.md R4_MASTER_CONTRACT.json UPSTREAM_PINS.json; do
  [ -f "$SRC/$f" ] || hold "BUNDLE_FILE_MISSING:$f"
  [ ! -L "$SRC/$f" ] || hold "BUNDLE_SYMLINK_REJECTED:$f"
done

echo
echo "============================================================"
echo " LOUKSNA R4 — MASTER PART 1 -> PART 9"
echo "============================================================"
echo "Checkpoint: 20260926T034746Z-38579"
echo "Modo: DIFFERENTIAL"
echo "Servidor: SERVER_READY ya certificado"
echo "Secuencia: PART_1 -> PART_2 -> ... -> PART_9"
echo
echo "Se validará sudo una sola vez para arrancar el ciclo gobernado."
echo

sudo -v
sudo -n /usr/local/sbin/louksna-apc status >/dev/null || hold "APC48_NOT_ACTIVE"

install -d -m 0700 "$DST" "$STATE"
install -d -m 0755 "$UNIT_DIR"
install -m 0700 "$SRC/master_controller.py" "$DST/master_controller.py"
install -m 0600 "$SRC/MASTER_MISSION.md" "$DST/MASTER_MISSION.md"
install -m 0600 "$SRC/R4_MASTER_CONTRACT.json" "$DST/R4_MASTER_CONTRACT.json"
install -m 0600 "$SRC/UPSTREAM_PINS.json" "$DST/UPSTREAM_PINS.json"

python3 -m py_compile "$DST/master_controller.py"

cat > "$UNIT.tmp" <<UNIT
[Unit]
Description=LOUKSNA R4 master PART1-PART9
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$DST
Environment=HOME=$HOME
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin
ExecStart=/usr/bin/python3 -B -I $DST/master_controller.py --loop --sleep 300
Restart=on-failure
RestartSec=15
PrivateTmp=yes
ProtectHome=false
LockPersonality=yes

[Install]
WantedBy=default.target
UNIT
mv "$UNIT.tmp" "$UNIT"
chmod 0600 "$UNIT"

systemctl --user daemon-reload
systemctl --user enable --now luna-r4-master-part1-part9.service

sleep 4

echo
echo "SERVICE=$(systemctl --user is-active luna-r4-master-part1-part9.service || true)"
echo "ENABLED=$(systemctl --user is-enabled luna-r4-master-part1-part9.service || true)"
echo

if [ -f "$STATE/MASTER_STATUS.json" ]; then
  cat "$STATE/MASTER_STATUS.json"
else
  echo "MASTER_STATUS=STARTING"
fi

echo
echo "============================================================"
echo " MASTER_R4_1_9=STARTED"
echo "============================================================"
echo "Estado: $STATE/MASTER_STATUS.json"
echo "Evidencia: $STATE/evidence/"
echo "Certificados: $STATE/certificates/"
echo "Logs: journalctl --user -u luna-r4-master-part1-part9.service -f"
echo
echo "La terminal puede cerrarse. systemd --user + linger mantienen el supervisor."
echo "PART 4 conservará H2/H4: no se ejecutará una operación destructiva sin ese gate."
