#!/bin/bash
set -Eeuo pipefail
umask 077

OWNER="diegoignacionorambuenamiranda"
HOST_EXPECTED="LOUKSNA"
APC="/usr/local/sbin/louksna-apc"
APC_SHA256_EXPECTED="e686c6e89026ec872cdccbc664601d31159aebabf07c203a4432ed77ad137ce6"
CFG="/etc/louksna-r4-apc/authorization.json"
SUDOERS_APC="/etc/sudoers.d/louksna-r4-apc"
TIMER_UNIT="/etc/systemd/system/louksna-r4-apc-revoke.timer"
RUNNER_UNIT="actions.runner.Plomillo-luna-linux-bridge.luna-linux.service"
RUNNER_DROPIN="/etc/systemd/system/${RUNNER_UNIT}.d/20-louksna-virtualization.conf"
EXPIRES_AT="2099-12-31T23:59:59Z"
EXPIRES_SUDO="20991231235959Z"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="/var/lib/louksna-part4-part9-permanent-permissions/backups/$STAMP"
EVIDENCE="$HOME/Descargas/LOUKSNA_PART4_PART9_PERMISSIONS_$STAMP.txt"

fail(){ echo "HOLD:$*" >&2; exit 1; }

[ "$#" -eq 0 ] || fail "NO_ARGUMENTS_ALLOWED"
[ "$(id -un)" = "$OWNER" ] || fail "OWNER_MISMATCH"
[ "$(hostname)" = "$HOST_EXPECTED" ] || fail "HOST_MISMATCH"

for cmd in /usr/bin/python3 /usr/bin/sha256sum /usr/sbin/visudo /usr/bin/systemctl /usr/sbin/usermod /usr/sbin/groupadd /usr/bin/getent /usr/bin/install; do
  [ -x "$cmd" ] || fail "MISSING_COMMAND:$cmd"
done

[ -x "$APC" ] || fail "APC_HELPER_MISSING"
[ -f "$CFG" ] || fail "APC_CONFIG_MISSING"
[ -f "$SUDOERS_APC" ] || fail "APC_SUDOERS_MISSING"

ACTUAL_APC_SHA="$(sha256sum "$APC" | awk '{print $1}')"
[ "$ACTUAL_APC_SHA" = "$APC_SHA256_EXPECTED" ] || fail "APC_HELPER_HASH_DRIFT:$ACTUAL_APC_SHA"

printf '%s\n' 'YO AUTORIZO explícitamente y de forma permanente las capacidades privilegiadas limitadas necesarias para LUNA R4 PART4→PART9: conservar APC sin expiración automática, acceso KVM/libvirt, servicios de virtualización/Waydroid allowlisted, módulos KVM/binder allowlisted y reboot gobernado por APC. NO autorizo sudo ALL, shell root arbitrario ni escritura root arbitraria.'
sudo -v

sudo install -d -m 0700 "$BACKUP_DIR"
for p in "$CFG" "$SUDOERS_APC" "$TIMER_UNIT" "$RUNNER_DROPIN"; do
  if sudo test -e "$p"; then
    sudo cp -a "$p" "$BACKUP_DIR/$(basename "$p").before"
  fi
done

# 1) Convierte la autorización APC existente en autorización persistente, sin mutar el helper certificado.
sudo python3 - "$CFG" "$EXPIRES_AT" <<'PY'
import datetime as dt, json, pathlib, sys, os
cfg_path, expires = sys.argv[1:]
p = pathlib.Path(cfg_path)
d = json.loads(p.read_text(encoding="utf-8"))
if d.get("status") != "ACTIVE":
    raise SystemExit("HOLD:APC_NOT_ACTIVE")
if d.get("owner") != "diegoignacionorambuenamiranda":
    raise SystemExit("HOLD:APC_OWNER_MISMATCH")
now = dt.datetime.now(dt.timezone.utc)
exp = dt.datetime.fromisoformat(expires.replace("Z","+00:00"))
d["expires_at_utc"] = expires
d["duration_hours"] = int((exp-now).total_seconds() // 3600)
d["authorization_mode"] = "PERMANENT_USER_EXPLICIT"
d["permanent_user_authorization"] = True
d["automatic_expiry"] = False
d["permanent_authorized_at_utc"] = now.isoformat().replace("+00:00","Z")
d["permanent_authorization_statement"] = "YO AUTORIZO"
scope=d.setdefault("authority_scope",{})
scope["sudo_all"]=False
scope["arbitrary_root_shell"]=False
scope["repository_mutation"]=False
scope["canonical_mutation"]=False
tmp=p.with_suffix(".tmp")
tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
os.chmod(tmp,0o644)
tmp.replace(p)
PY

# 2) Sudo sin contraseña sólo para el helper APC exacto, con horizonte 2099.
TMP_SUDOERS="$(mktemp)"
trap 'rm -f "$TMP_SUDOERS"' EXIT
printf '%s ALL=(root) NOTAFTER=%s NOPASSWD: %s\n' "$OWNER" "$EXPIRES_SUDO" "$APC" > "$TMP_SUDOERS"
chmod 0440 "$TMP_SUDOERS"
sudo /usr/sbin/visudo -cf "$TMP_SUDOERS" >/dev/null
sudo install -o root -g root -m 0440 "$TMP_SUDOERS" "$SUDOERS_APC"
sudo /usr/sbin/visudo -c >/dev/null

# 3) Retira únicamente la revocación automática por reloj; la revocación manual APC sigue existiendo.
sudo systemctl disable --now louksna-r4-apc-revoke.timer >/dev/null 2>&1 || true
if sudo test -f "$TIMER_UNIT"; then
  sudo mv "$TIMER_UNIT" "$BACKUP_DIR/louksna-r4-apc-revoke.timer.disabled"
fi

# 4) Prepara grupos permanentes KVM/libvirt.
getent group kvm >/dev/null || sudo groupadd --system kvm
getent group libvirt >/dev/null || sudo groupadd --system libvirt
sudo usermod -aG kvm,libvirt "$OWNER"

# 5) Garantiza que el runner reciba esos grupos aun antes de un nuevo inicio de sesión.
sudo install -d -m 0755 "$(dirname "$RUNNER_DROPIN")"
cat <<'UNIT' | sudo tee "$RUNNER_DROPIN" >/dev/null
[Service]
SupplementaryGroups=kvm libvirt
UNIT

# 6) Allowlist adicional, sin shell/root global, para servicios/módulos que pueden aparecer en PART5/PART6.
EXTRA_SUDOERS="/etc/sudoers.d/louksna-part5-part9-services"
TMP_EXTRA="$(mktemp)"
trap 'rm -f "$TMP_SUDOERS" "$TMP_EXTRA"' EXIT
cat > "$TMP_EXTRA" <<EOF
Cmnd_Alias LOUKSNA_R4_VIRT_SERVICES = \
 /usr/bin/systemctl start libvirtd.service, \
 /usr/bin/systemctl stop libvirtd.service, \
 /usr/bin/systemctl restart libvirtd.service, \
 /usr/bin/systemctl enable libvirtd.service, \
 /usr/bin/systemctl disable libvirtd.service, \
 /usr/bin/systemctl start libvirtd.socket, \
 /usr/bin/systemctl stop libvirtd.socket, \
 /usr/bin/systemctl restart libvirtd.socket, \
 /usr/bin/systemctl enable libvirtd.socket, \
 /usr/bin/systemctl disable libvirtd.socket, \
 /usr/bin/systemctl start virtlogd.service, \
 /usr/bin/systemctl stop virtlogd.service, \
 /usr/bin/systemctl restart virtlogd.service, \
 /usr/bin/systemctl start virtlockd.service, \
 /usr/bin/systemctl stop virtlockd.service, \
 /usr/bin/systemctl restart virtlockd.service, \
 /usr/bin/systemctl start waydroid-container.service, \
 /usr/bin/systemctl stop waydroid-container.service, \
 /usr/bin/systemctl restart waydroid-container.service, \
 /usr/bin/systemctl daemon-reload
Cmnd_Alias LOUKSNA_R4_KERNEL_MODULES = \
 /usr/sbin/modprobe kvm, \
 /usr/sbin/modprobe kvm_amd, \
 /usr/sbin/modprobe binder_linux
$OWNER ALL=(root) NOPASSWD: LOUKSNA_R4_VIRT_SERVICES, LOUKSNA_R4_KERNEL_MODULES
EOF
chmod 0440 "$TMP_EXTRA"
sudo /usr/sbin/visudo -cf "$TMP_EXTRA" >/dev/null
sudo install -o root -g root -m 0440 "$TMP_EXTRA" "$EXTRA_SUDOERS"
sudo /usr/sbin/visudo -c >/dev/null

sudo systemctl daemon-reload

# Carga KVM cuando esté disponible; binder se deja bajo demanda para Waydroid.
sudo -n /usr/sbin/modprobe kvm || true
sudo -n /usr/sbin/modprobe kvm_amd || true

# Evita cortar un GitHub job activo; espera hasta 5 minutos y luego reinicia el runner.
for _ in $(seq 1 60); do
  pgrep -f '[R]unner.Worker' >/dev/null 2>&1 || break
  sleep 5
done
if pgrep -f '[R]unner.Worker' >/dev/null 2>&1; then
  fail "RUNNER_BUSY_RESTART_DEFERRED"
fi
sudo systemctl restart "$RUNNER_UNIT"
sleep 2
[ "$(systemctl is-active "$RUNNER_UNIT")" = "active" ] || fail "RUNNER_RESTART_FAILED"

# 7) Pruebas finales.
sudo -n "$APC" status > /tmp/louksna-apc-permanent-status.json
python3 - /tmp/louksna-apc-permanent-status.json "$EXPIRES_AT" <<'PY'
import json,sys
p,exp=sys.argv[1:]
d=json.load(open(p,encoding="utf-8"))
assert d["status"]=="ACTIVE"
assert d["authorization_valid"] is True
assert d["expires_at_utc"]==exp
PY

findmnt -T "/media/$OWNER/Windows/PROYECTOS" -no OPTIONS | grep -qw rw || fail "PROYECTOS_NOT_RW"
id -nG "$OWNER" | tr ' ' '\n' | grep -qx kvm || fail "KVM_GROUP_NOT_GRANTED"
id -nG "$OWNER" | tr ' ' '\n' | grep -qx libvirt || fail "LIBVIRT_GROUP_NOT_GRANTED"

{
  echo "schema=LOUKSNA_R4_PART4_PART9_PERMANENT_PERMISSIONS/1.0"
  echo "status=PASS"
  echo "timestamp_utc=$(date -u +%FT%TZ)"
  echo "owner=$OWNER"
  echo "apc_helper_sha256=$ACTUAL_APC_SHA"
  echo "apc_expires_at_utc=$EXPIRES_AT"
  echo "apc_automatic_expiry=DISABLED"
  echo "groups=$(id -nG "$OWNER")"
  echo "runner=$(systemctl is-active "$RUNNER_UNIT")"
  echo "kvm_device=$(test -e /dev/kvm && echo PRESENT || echo ABSENT)"
  echo "proyectos=$(findmnt -T "/media/$OWNER/Windows/PROYECTOS" -no SOURCE,FSTYPE,OPTIONS,TARGET)"
  echo "sudoers_global_all=FALSE"
  echo "arbitrary_root_shell=FALSE"
  echo "manual_apc_revoke=AVAILABLE"
  echo "--- APC STATUS ---"
  cat /tmp/louksna-apc-permanent-status.json
} | tee "$EVIDENCE"

rm -f /tmp/louksna-apc-permanent-status.json
echo "PASS: permisos permanentes limitados PART4→PART9 activados."
echo "EVIDENCE=$EVIDENCE"
echo "ROLLBACK_BACKUP=$BACKUP_DIR"
