#!/bin/bash
set -Eeuo pipefail
umask 077

REASON="${1:-unspecified}"
CFG="/etc/louksna-r4-apc/authorization.json"
SUDOERS="/etc/sudoers.d/louksna-r4-apc"
AUDIT_DIR="/var/log/louksna-r4-apc"
AUDIT="$AUDIT_DIR/audit.jsonl"
HELPER="/usr/local/sbin/louksna-apc"
AWAKE_UNIT="/etc/systemd/system/louksna-r4-awake.service"
REVOKE_SERVICE="/etc/systemd/system/louksna-r4-apc-revoke.service"
REVOKE_TIMER="/etc/systemd/system/louksna-r4-apc-revoke.timer"

mkdir -p "$AUDIT_DIR"
chmod 0700 "$AUDIT_DIR"

python3 - "$REASON" "$AUDIT" "$CFG" <<'PY'
import datetime as dt, json, pathlib, sys, os
reason,audit_path,cfg_path=sys.argv[1:]
utc=dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z")
audit=pathlib.Path(audit_path)
with audit.open("a",encoding="utf-8") as f:
    f.write(json.dumps({
        "utc":utc,
        "action":"revoke",
        "status":"START",
        "reason":reason,
        "pid":os.getpid()
    },sort_keys=True)+"\n")
    f.flush(); os.fsync(f.fileno())
cfg=pathlib.Path(cfg_path)
if cfg.is_file():
    try:
        data=json.loads(cfg.read_text(encoding="utf-8"))
    except Exception:
        data={}
    data["status"]="REVOKED"
    data["revoked_at_utc"]=utc
    data["revoke_reason"]=reason
    tmp=cfg.with_suffix(".tmp")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.chmod(tmp,0o644)
    tmp.replace(cfg)
PY

/usr/bin/systemctl disable --now louksna-r4-awake.service >/dev/null 2>&1 || true
/usr/bin/systemctl disable --now louksna-r4-apc-revoke.timer >/dev/null 2>&1 || true
rm -f -- "$SUDOERS" "$HELPER" "$AWAKE_UNIT" "$REVOKE_SERVICE" "$REVOKE_TIMER"
/usr/bin/systemctl daemon-reload >/dev/null 2>&1 || true
/usr/sbin/visudo -c >/dev/null

python3 - "$REASON" "$AUDIT" <<'PY'
import datetime as dt, json, pathlib, sys, os
reason,audit_path=sys.argv[1:]
utc=dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z")
audit=pathlib.Path(audit_path)
with audit.open("a",encoding="utf-8") as f:
    f.write(json.dumps({
        "utc":utc,
        "action":"revoke",
        "status":"PASS",
        "reason":reason,
        "sudoers_removed":True,
        "helper_removed":True,
        "awake_disabled":True,
        "timer_disabled":True,
        "unit_files_removed":True,
        "pid":os.getpid()
    },sort_keys=True)+"\n")
    f.flush(); os.fsync(f.fileno())
PY

exit 0
