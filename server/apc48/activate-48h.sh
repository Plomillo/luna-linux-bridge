#!/bin/bash
set -Eeuo pipefail
umask 077

OWNER="diegoignacionorambuenamiranda"
OWNER_HOME="/home/$OWNER"
HOST_EXPECTED="LOUKSNA"
SELF_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER_SRC="$SELF_DIR/louksna_apc.py"
REVOKE_SRC="$SELF_DIR/louksna_apc_revoke.sh"
CHECKPOINT="$OWNER_HOME/LOUKSNA_MAESTRO_20260925/MISSION3_OPERATIVE/R4_PART1_DESKTOP_V1/runs/20260926T034746Z-38579"
UI_REF="$OWNER_HOME/Descargas/LUNA_R4_UI_REFERENCE"
IMAGE_SHA_EXPECTED="8a9852c4155d64fd74059c7239e67c82e16e5acd556627d70575db85078d4ed4"
KDE_SHA_EXPECTED="c21e04d5447e123b59fc9b94d2e9684bc03ea164999ef6f60210e257557a16dc"
SERVER_READY_RUN="36503769931"
APC_HOURS="48"

HELPER_DST="/usr/local/sbin/louksna-apc"
REVOKE_DST="/usr/local/libexec/louksna-r4-apc-revoke"
CFG_DIR="/etc/louksna-r4-apc"
CFG="$CFG_DIR/authorization.json"
SUDOERS="/etc/sudoers.d/louksna-r4-apc"
STATE_DIR="/var/lib/louksna-r4-apc"
LOG_DIR="/var/log/louksna-r4-apc"
AWAKE_UNIT="/etc/systemd/system/louksna-r4-awake.service"
REVOKE_SERVICE="/etc/systemd/system/louksna-r4-apc-revoke.service"
REVOKE_TIMER="/etc/systemd/system/louksna-r4-apc-revoke.timer"
RUNNER_UNIT="actions.runner.Plomillo-luna-linux-bridge.luna-linux.service"

fail() {
  echo "HOLD:$*" >&2
  exit 1
}

if [ "$#" -ne 0 ]; then
  fail "NO_ARGUMENTS_ALLOWED"
fi
if [ "${EUID}" -ne 0 ]; then
  fail "RUN_WITH_SUDO"
fi
if [ "${SUDO_USER:-}" != "$OWNER" ]; then
  fail "SUDO_USER_MISMATCH expected=$OWNER actual=${SUDO_USER:-unset}"
fi
if [ "$(hostname)" != "$HOST_EXPECTED" ]; then
  fail "HOST_MISMATCH expected=$HOST_EXPECTED actual=$(hostname)"
fi

for cmd in /usr/sbin/visudo /usr/bin/python3 /usr/bin/systemctl /usr/bin/systemd-inhibit /usr/bin/sha256sum /usr/bin/date /usr/bin/install /usr/sbin/runuser /usr/bin/journalctl; do
  [ -x "$cmd" ] || fail "MISSING_COMMAND:$cmd"
done
[ -f "$HELPER_SRC" ] || fail "HELPER_SOURCE_MISSING"
[ -f "$REVOKE_SRC" ] || fail "REVOKE_SOURCE_MISSING"
[ -d "$CHECKPOINT" ] || fail "CHECKPOINT_MISSING"
for f in CHECKPOINT.json LAUNCHERS.json PANEL_CREATED.json RUNTIME_VERIFY.json; do
  [ -f "$CHECKPOINT/$f" ] || fail "CHECKPOINT_EVIDENCE_MISSING:$f"
done
[ -d "$UI_REF" ] || fail "UI_REFERENCE_MISSING"

IMAGE_SHA="$(sha256sum "$UI_REF/LUNA_R4_UI_REFERENCE_PARTS_1_9.jpg" | awk '{print $1}')"
KDE_SHA="$(sha256sum "$UI_REF/KDE_UI_REFERENCE_20260929T020349Z.7z" | awk '{print $1}')"
[ "$IMAGE_SHA" = "$IMAGE_SHA_EXPECTED" ] || fail "UI_IMAGE_HASH_MISMATCH"
[ "$KDE_SHA" = "$KDE_SHA_EXPECTED" ] || fail "UI_KDE_HASH_MISMATCH"

RUNNER_STATE="$(systemctl is-active "$RUNNER_UNIT" 2>/dev/null || true)"
[ "$RUNNER_STATE" = "active" ] || fail "RUNNER_NOT_ACTIVE:$RUNNER_STATE"

OWNER_UID="$(id -u "$OWNER")"
OWNER_BUS="/run/user/$OWNER_UID/bus"
SYMPHYLAX_STATE="$(runuser -u "$OWNER" -- env XDG_RUNTIME_DIR="/run/user/$OWNER_UID" DBUS_SESSION_BUS_ADDRESS="unix:path=$OWNER_BUS" systemctl --user is-active symphylax-r1.service 2>/dev/null || true)"
[ "$SYMPHYLAX_STATE" = "active" ] || fail "SYMPHYLAX_NOT_ACTIVE:$SYMPHYLAX_STATE"
LINGER="$(loginctl show-user "$OWNER" -p Linger --value 2>/dev/null || true)"
[ "$LINGER" = "yes" ] || fail "LINGER_NOT_ENABLED"

install -d -m 0755 "$STATE_DIR"
install -d -m 0700 "$LOG_DIR"
RECOVERY_DIR="$STATE_DIR/recovery/$(date -u '+%Y%m%dT%H%M%SZ')"
RECOVERY_PERFORMED=0

# Recover only a previously revoked/incomplete APC. Never overwrite an active one.
if [ -f "$CFG" ] || [ -e "$HELPER_DST" ] || [ -e "$SUDOERS" ] || [ -e "$AWAKE_UNIT" ] || [ -e "$REVOKE_TIMER" ]; then
  EXISTING_STATUS="UNKNOWN"
  if [ -f "$CFG" ]; then
    EXISTING_STATUS="$(python3 - "$CFG" <<'PY'
import json,sys
try:
    print(json.load(open(sys.argv[1],encoding="utf-8")).get("status","UNKNOWN"))
except Exception:
    print("INVALID")
PY
)"
  fi

  if [ "$EXISTING_STATUS" = "ACTIVE" ]; then
    fail "ACTIVE_APC_ALREADY_PRESENT_NO_EXTENSION"
  fi
  if [ "$EXISTING_STATUS" != "REVOKED" ] && [ "$EXISTING_STATUS" != "UNKNOWN" ]; then
    fail "UNSAFE_PREVIOUS_APC_STATE:$EXISTING_STATUS"
  fi

  install -d -m 0700 "$RECOVERY_DIR"
  if [ -f "$CFG" ]; then
    cp -a "$CFG" "$RECOVERY_DIR/authorization.before.json"
  fi
  systemctl show louksna-r4-awake.service -p LoadState -p ActiveState -p SubState -p Result -p ExecMainStatus -p UnitFileState > "$RECOVERY_DIR/awake.before.txt" 2>&1 || true
  systemctl show louksna-r4-apc-revoke.timer -p LoadState -p ActiveState -p SubState -p Result -p UnitFileState -p NextElapseUSecRealtime > "$RECOVERY_DIR/timer.before.txt" 2>&1 || true
  journalctl -u louksna-r4-awake.service -b --no-pager -n 120 > "$RECOVERY_DIR/awake.journal.txt" 2>&1 || true

  systemctl disable --now louksna-r4-awake.service >/dev/null 2>&1 || true
  systemctl disable --now louksna-r4-apc-revoke.timer >/dev/null 2>&1 || true
  rm -f -- "$SUDOERS" "$HELPER_DST" "$REVOKE_DST" "$AWAKE_UNIT" "$REVOKE_SERVICE" "$REVOKE_TIMER"
  rm -rf -- "$CFG_DIR"
  rm -f -- "$STATE_DIR/NOPASSWD_PROOF.json" "$STATE_DIR/ACTIVATION_EVIDENCE.json"
  systemctl daemon-reload
  RECOVERY_PERFORMED=1
  echo "PREVIOUS_REVOKED_APC_RECOVERY=PASS"
  echo "RECOVERY_EVIDENCE=$RECOVERY_DIR"
fi

for p in "$HELPER_DST" "$REVOKE_DST" "$SUDOERS" "$AWAKE_UNIT" "$REVOKE_SERVICE" "$REVOKE_TIMER"; do
  [ ! -e "$p" ] || fail "TARGET_ALREADY_EXISTS_AFTER_RECOVERY:$p"
done

CREATED_AT="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
EXPIRES_AT="$(date -u -d "+$APC_HOURS hours" '+%Y-%m-%dT%H:%M:%SZ')"
EXPIRES_SUDO="$(date -u -d "+$APC_HOURS hours" '+%Y%m%d%H%M%SZ')"
EXPIRES_CAL="$(date -u -d "+$APC_HOURS hours" '+%Y-%m-%d %H:%M:%S UTC')"
BOOT_ID="$(cat /proc/sys/kernel/random/boot_id)"
HELPER_SHA="$(sha256sum "$HELPER_SRC" | awk '{print $1}')"
REVOKE_SHA="$(sha256sum "$REVOKE_SRC" | awk '{print $1}')"

CLEANUP_NEEDED=1
cleanup_on_exit() {
  rc=$?
  if [ "$rc" -ne 0 ] && [ "$CLEANUP_NEEDED" -eq 1 ]; then
    echo "ROLLBACK:activation failed rc=$rc" >&2
    systemctl disable --now louksna-r4-awake.service >/dev/null 2>&1 || true
    systemctl disable --now louksna-r4-apc-revoke.timer >/dev/null 2>&1 || true
    rm -f -- "$SUDOERS" "$HELPER_DST" "$REVOKE_DST" "$AWAKE_UNIT" "$REVOKE_SERVICE" "$REVOKE_TIMER"
    rm -rf -- "$CFG_DIR"
    rm -f -- "$STATE_DIR/NOPASSWD_PROOF.json" "$STATE_DIR/ACTIVATION_EVIDENCE.json"
    systemctl daemon-reload >/dev/null 2>&1 || true
  fi
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

install -d -m 0755 /usr/local/libexec "$CFG_DIR"
install -o root -g root -m 0755 "$HELPER_SRC" "$HELPER_DST"
install -o root -g root -m 0755 "$REVOKE_SRC" "$REVOKE_DST"

python3 - "$CFG" "$CREATED_AT" "$EXPIRES_AT" "$CHECKPOINT" "$UI_REF" "$IMAGE_SHA" "$KDE_SHA" "$SERVER_READY_RUN" "$HELPER_SHA" "$REVOKE_SHA" "$BOOT_ID" "$RECOVERY_PERFORMED" "$RECOVERY_DIR" <<'PY'
import json,sys,os,pathlib
(cfg,created,expires,checkpoint,ui,image_sha,kde_sha,server_run,helper_sha,revoke_sha,boot_id,recovery_performed,recovery_dir)=sys.argv[1:]
obj={
  "schema":"LOUKSNA_R4_APC_AUTHORIZATION/2.0",
  "status":"ACTIVE",
  "owner":"diegoignacionorambuenamiranda",
  "created_at_utc":created,
  "expires_at_utc":expires,
  "duration_hours":48,
  "host":"LOUKSNA",
  "boot_id_at_activation":boot_id,
  "resume_checkpoint":checkpoint,
  "ui_reference":ui,
  "ui_hashes":{"image":image_sha,"kde_snapshot":kde_sha},
  "start_part":"PART_1",
  "resume_mode":"DIFFERENTIAL",
  "part2_gate":"PART1_POST_VALIDATION_PASS",
  "server_ready_run":int(server_run),
  "server_ready_certified":True,
  "repeat_server_ready":False,
  "helper_sha256":helper_sha,
  "revoke_sha256":revoke_sha,
  "recovery":{"performed":recovery_performed=="1","evidence_dir":recovery_dir if recovery_performed=="1" else None},
  "authority_scope":{
    "arbitrary_root_shell":False,
    "sudo_all":False,
    "repository_mutation":False,
    "canonical_mutation":False,
    "allowed":["status","audit-tail","awake-start","awake-stop","apt-update","apt-install","apt-repair","service:allowlist","reboot:rate-limited","revoke"]
  },
  "resume_contract":{
    "do_not_repeat":["PART_0","PART_1_FULL_REINSTALL","SERVER_READY_G08_G09_G23_G24"],
    "first":"VERIFY_CURRENT_PART1_AGAINST_CHECKPOINT_AND_APPROVED_UI_REFERENCE",
    "then":"APPLY_ONLY_MISSING_PART1_DELTA",
    "part2_entry":"ONLY_AFTER_PART1_POST_VALIDATION_PASS",
    "failure_posture":"FAIL_CLOSED"
  }
}
p=pathlib.Path(cfg)
tmp=p.with_suffix(".tmp")
tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
os.chmod(tmp,0o644)
tmp.replace(p)
PY

cat > "$AWAKE_UNIT" <<'UNIT'
[Unit]
Description=LOUKSNA R4 installation awake guard
After=systemd-logind.service
ConditionPathExists=/etc/louksna-r4-apc/authorization.json

[Service]
Type=simple
ExecStart=/usr/bin/systemd-inhibit --what=sleep:idle:handle-lid-switch --who=LOUKSNA-R4-APC --why=LOUKSNA-R4-governed-installation-window --mode=block /usr/bin/sleep infinity
Restart=on-failure
RestartSec=3
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=read-only
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes

[Install]
WantedBy=multi-user.target
UNIT

cat > "$REVOKE_SERVICE" <<'UNIT'
[Unit]
Description=Revoke LOUKSNA R4 APC authorization

[Service]
Type=oneshot
ExecStart=/usr/local/libexec/louksna-r4-apc-revoke expiry
UNIT

cat > "$REVOKE_TIMER" <<UNIT
[Unit]
Description=Expire LOUKSNA R4 APC authorization at absolute 48h deadline

[Timer]
OnCalendar=$EXPIRES_CAL
Persistent=true
AccuracySec=1min
Unit=louksna-r4-apc-revoke.service

[Install]
WantedBy=timers.target
UNIT

cat > "$SUDOERS.tmp" <<EOF
$OWNER ALL=(root) NOTAFTER=$EXPIRES_SUDO NOPASSWD: /usr/local/sbin/louksna-apc
EOF
chmod 0440 "$SUDOERS.tmp"
/usr/sbin/visudo -cf "$SUDOERS.tmp" >/dev/null
mv "$SUDOERS.tmp" "$SUDOERS"
chmod 0440 "$SUDOERS"
/usr/sbin/visudo -c >/dev/null

systemctl daemon-reload
systemctl enable --now louksna-r4-awake.service
systemctl enable --now louksna-r4-apc-revoke.timer

for _ in 1 2 3 4 5; do
  [ "$(systemctl is-active louksna-r4-awake.service 2>/dev/null || true)" = "active" ] && break
  sleep 1
done
[ "$(systemctl is-active louksna-r4-awake.service 2>/dev/null || true)" = "active" ] || fail "AWAKE_GUARD_NOT_ACTIVE"

AWAKE_PID_1="$(systemctl show louksna-r4-awake.service -p MainPID --value)"
[ "$AWAKE_PID_1" != "0" ] || fail "AWAKE_GUARD_PID_ZERO"
sleep 2
[ "$(systemctl is-active louksna-r4-awake.service 2>/dev/null || true)" = "active" ] || fail "AWAKE_GUARD_NOT_STABLE"
AWAKE_PID_2="$(systemctl show louksna-r4-awake.service -p MainPID --value)"
[ "$AWAKE_PID_2" = "$AWAKE_PID_1" ] || fail "AWAKE_GUARD_PID_CHANGED_DURING_STABILITY_WINDOW"

[ "$(systemctl is-active louksna-r4-apc-revoke.timer 2>/dev/null || true)" = "active" ] || fail "REVOCATION_TIMER_NOT_ACTIVE"

runuser -u "$OWNER" -- sudo -n /usr/local/sbin/louksna-apc status > "$STATE_DIR/NOPASSWD_PROOF.json"
chmod 0644 "$STATE_DIR/NOPASSWD_PROOF.json"

HELPER_DST_SHA="$(sha256sum "$HELPER_DST" | awk '{print $1}')"
REVOKE_DST_SHA="$(sha256sum "$REVOKE_DST" | awk '{print $1}')"
SUDOERS_SHA="$(sha256sum "$SUDOERS" | awk '{print $1}')"
AWAKE_SHA="$(sha256sum "$AWAKE_UNIT" | awk '{print $1}')"
TIMER_SHA="$(sha256sum "$REVOKE_TIMER" | awk '{print $1}')"

[ "$HELPER_DST_SHA" = "$HELPER_SHA" ] || fail "HELPER_INSTALL_HASH_MISMATCH"
[ "$REVOKE_DST_SHA" = "$REVOKE_SHA" ] || fail "REVOKE_INSTALL_HASH_MISMATCH"

python3 - "$STATE_DIR/ACTIVATION_EVIDENCE.json" "$CREATED_AT" "$EXPIRES_AT" "$BOOT_ID" "$HELPER_DST_SHA" "$REVOKE_DST_SHA" "$SUDOERS_SHA" "$AWAKE_SHA" "$TIMER_SHA" "$IMAGE_SHA" "$KDE_SHA" "$AWAKE_PID_2" "$RECOVERY_PERFORMED" "$RECOVERY_DIR" <<'PY'
import json,sys,os,pathlib
(out,created,expires,boot,helper,revoke,sudoers,awake,timer,image,kde,awake_pid,recovery_performed,recovery_dir)=sys.argv[1:]
obj={
 "schema":"LOUKSNA_R4_APC_ACTIVATION_EVIDENCE/2.0",
 "status":"PASS",
 "created_at_utc":created,
 "expires_at_utc":expires,
 "boot_id":boot,
 "host":"LOUKSNA",
 "runner_active":True,
 "symphylax_active":True,
 "linger":True,
 "nopasswd_proof":"PASS",
 "awake_guard":"ACTIVE_STABLE",
 "awake_main_pid":int(awake_pid),
 "automatic_revoke_timer":"ACTIVE",
 "recovery":{"performed":recovery_performed=="1","evidence_dir":recovery_dir if recovery_performed=="1" else None},
 "hashes":{
   "helper":helper,"revoke":revoke,"sudoers":sudoers,
   "awake_unit":awake,"revoke_timer":timer,
   "ui_image":image,"ui_kde_snapshot":kde
 },
 "resume":{
   "part":"PART_1",
   "mode":"DIFFERENTIAL",
   "checkpoint":"/home/diegoignacionorambuenamiranda/LOUKSNA_MAESTRO_20260925/MISSION3_OPERATIVE/R4_PART1_DESKTOP_V1/runs/20260926T034746Z-38579",
   "part2_gate":"PART1_POST_VALIDATION_PASS"
 },
 "security":{
   "password_stored":False,
   "nopasswd_all":False,
   "arbitrary_root_shell":False,
   "canonical_mutation":False,
   "automatic_expiry_hard_bound":"sudoers NOTAFTER + systemd timer",
   "transactional_rollback":"EXIT_TRAP"
 }
}
p=pathlib.Path(out)
p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
os.chmod(p,0o644)
PY

cp -f "$STATE_DIR/ACTIVATION_EVIDENCE.json" "$SELF_DIR/ACTIVATION_EVIDENCE.json"
chown "$OWNER:$OWNER" "$SELF_DIR/ACTIVATION_EVIDENCE.json"
chmod 0644 "$SELF_DIR/ACTIVATION_EVIDENCE.json"

CLEANUP_NEEDED=0
trap - EXIT INT TERM

echo
echo "============================================================"
echo "LOUKSNA R4 APC 48H V2 = ACTIVADO"
echo "============================================================"
echo "CREATED_AT_UTC=$CREATED_AT"
echo "EXPIRES_AT_UTC=$EXPIRES_AT"
echo "RESUME_FROM=$CHECKPOINT"
echo "START_PART=PART_1"
echo "MODE=DIFFERENTIAL"
echo "PART2_GATE=PART1_POST_VALIDATION_PASS"
echo "RUNNER=active"
echo "SYMPHYLAX=active"
echo "LINGER=yes"
echo "AWAKE_GUARD=active_stable"
echo "AWAKE_MAIN_PID=$AWAKE_PID_2"
echo "NOPASSWD_PROOF=PASS"
echo "RECOVERY_PERFORMED=$RECOVERY_PERFORMED"
echo
echo "Estado:"
runuser -u "$OWNER" -- sudo -n /usr/local/sbin/louksna-apc status
echo
echo "Revocacion manual:"
echo "  sudo -n /usr/local/sbin/louksna-apc revoke"
