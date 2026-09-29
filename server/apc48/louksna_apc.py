#!/usr/bin/python3
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

OWNER = "diegoignacionorambuenamiranda"
CONFIG = pathlib.Path("/etc/louksna-r4-apc/authorization.json")
AUDIT_DIR = pathlib.Path("/var/log/louksna-r4-apc")
AUDIT = AUDIT_DIR / "audit.jsonl"
STATE_DIR = pathlib.Path("/var/lib/louksna-r4-apc")
REBOOT_STATE = STATE_DIR / "reboots.json"
REVOKE = pathlib.Path("/usr/local/libexec/louksna-r4-apc-revoke")
AWAKE_UNIT = "louksna-r4-awake.service"
RUNNER_UNIT = "actions.runner.Plomillo-luna-linux-bridge.luna-linux.service"
ALLOWED_UNITS = {AWAKE_UNIT, RUNNER_UNIT}
ALLOWED_SERVICE_ACTIONS = {"start", "stop", "restart", "enable", "disable", "status", "is-active", "is-enabled"}
PKG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+._-]*(?::[A-Za-z0-9][A-Za-z0-9_-]*)?(?:=[A-Za-z0-9:+.~_-]+)?$")
ENV = {
    "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "DEBIAN_FRONTEND": "noninteractive",
}

def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)

def iso(t: dt.datetime | None = None) -> str:
    return (t or now()).astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")

def die(msg: str, code: int = 2) -> "NoReturn":
    print(f"HOLD:{msg}", file=sys.stderr)
    raise SystemExit(code)

def load_config() -> dict:
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"CONFIG_INVALID:{e}", 10)
    if data.get("owner") != OWNER:
        die("OWNER_MISMATCH", 11)
    return data

def expires_at(cfg: dict) -> dt.datetime:
    raw = str(cfg.get("expires_at_utc", ""))
    try:
        return dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except Exception:
        die("EXPIRY_INVALID", 12)

def authorization_valid(cfg: dict) -> bool:
    return cfg.get("status") == "ACTIVE" and now() < expires_at(cfg)

def ensure_authorized(cfg: dict) -> None:
    if os.geteuid() != 0:
        die("ROOT_REQUIRED", 13)
    sudo_user = os.environ.get("SUDO_USER", "")
    if sudo_user not in ("", OWNER, "root"):
        die("CALLER_NOT_AUTHORIZED", 14)
    if not authorization_valid(cfg):
        die("AUTHORIZATION_EXPIRED_OR_INACTIVE", 15)

def append_audit(action: str, args: list[str], status: str, rc: int | None = None, detail: str | None = None) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(AUDIT_DIR, 0o700)
    rec = {
        "utc": iso(),
        "action": action,
        "args": args,
        "status": status,
        "rc": rc,
        "detail": detail,
        "euid": os.geteuid(),
        "sudo_user": os.environ.get("SUDO_USER"),
        "pid": os.getpid(),
    }
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.chmod(AUDIT, 0o600)

def run(cmd: list[str], action: str) -> int:
    append_audit(action, cmd[1:], "START")
    p = subprocess.run(cmd, env=ENV, stdin=subprocess.DEVNULL)
    append_audit(action, cmd[1:], "PASS" if p.returncode == 0 else "FAIL", p.returncode)
    return p.returncode

def verify_reference(cfg: dict) -> None:
    import hashlib
    ref = pathlib.Path(cfg["ui_reference"])
    expected = cfg["ui_hashes"]
    pairs = {
        "image": ref / "LUNA_R4_UI_REFERENCE_PARTS_1_9.jpg",
        "kde_snapshot": ref / "KDE_UI_REFERENCE_20260929T020349Z.7z",
    }
    for key, p in pairs.items():
        if not p.is_file():
            die(f"REFERENCE_MISSING:{p}", 20)
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h != expected[key]:
            die(f"REFERENCE_HASH_MISMATCH:{key}:{h}", 21)
    cp = pathlib.Path(cfg["resume_checkpoint"])
    if not cp.is_dir():
        die("RESUME_CHECKPOINT_MISSING", 22)
    for req in ("CHECKPOINT.json", "LAUNCHERS.json", "PANEL_CREATED.json", "RUNTIME_VERIFY.json"):
        if not (cp / req).is_file():
            die(f"CHECKPOINT_EVIDENCE_MISSING:{req}", 23)

def status(cfg: dict) -> int:
    out = {
        "schema": "LOUKSNA_R4_APC_STATUS/1.0",
        "status": cfg.get("status"),
        "authorization_valid": authorization_valid(cfg),
        "created_at_utc": cfg.get("created_at_utc"),
        "expires_at_utc": cfg.get("expires_at_utc"),
        "remaining_seconds": max(0, int((expires_at(cfg) - now()).total_seconds())),
        "owner": cfg.get("owner"),
        "resume_checkpoint": cfg.get("resume_checkpoint"),
        "ui_reference": cfg.get("ui_reference"),
        "start_part": cfg.get("start_part"),
        "resume_mode": cfg.get("resume_mode"),
        "part2_gate": cfg.get("part2_gate"),
        "server_ready_run": cfg.get("server_ready_run"),
        "allowed_actions": [
            "status", "audit-tail", "awake-start", "awake-stop",
            "apt-update", "apt-install", "apt-repair",
            "service", "reboot", "revoke"
        ],
        "security": {
            "arbitrary_shell": False,
            "arbitrary_file_write": False,
            "apt_repository_mutation": False,
            "local_deb_install": False,
            "service_allowlist": sorted(ALLOWED_UNITS),
            "reboot_rate_limit": "max 3 requests / 2 hours",
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0

def audit_tail(args: list[str]) -> int:
    n = 50
    if args:
        try:
            n = int(args[0])
        except ValueError:
            die("AUDIT_TAIL_INVALID", 30)
    n = max(1, min(n, 200))
    if not AUDIT.is_file():
        return 0
    lines = AUDIT.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    print("\n".join(lines))
    return 0

def validate_packages(pkgs: list[str]) -> None:
    if not pkgs or len(pkgs) > 64:
        die("PACKAGE_COUNT_INVALID", 40)
    for p in pkgs:
        if p.startswith("-") or "/" in p or not PKG_RE.fullmatch(p):
            die(f"PACKAGE_REJECTED:{p}", 41)

def reboot_guard(cfg: dict) -> None:
    verify_reference(cfg)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE_DIR, 0o755)
    history: list[float] = []
    if REBOOT_STATE.is_file():
        try:
            history = [float(x) for x in json.loads(REBOOT_STATE.read_text()).get("epochs", [])]
        except Exception:
            history = []
    cutoff = time.time() - 7200
    history = [x for x in history if x >= cutoff]
    if len(history) >= 3:
        die("REBOOT_RATE_LIMIT", 50)
    history.append(time.time())
    tmp = REBOOT_STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"epochs": history, "updated_at_utc": iso()}, indent=2) + "\n")
    os.chmod(tmp, 0o600)
    tmp.replace(REBOOT_STATE)

def main(argv: list[str]) -> int:
    cfg = load_config()
    if len(argv) < 2:
        return status(cfg)
    action, args = argv[1], argv[2:]

    if action == "status":
        return status(cfg)
    if action == "audit-tail":
        ensure_authorized(cfg)
        return audit_tail(args)

    ensure_authorized(cfg)

    if action == "awake-start":
        return run(["/usr/bin/systemctl", "start", AWAKE_UNIT], action)
    if action == "awake-stop":
        return run(["/usr/bin/systemctl", "stop", AWAKE_UNIT], action)
    if action == "apt-update":
        verify_reference(cfg)
        return run(["/usr/bin/apt-get", "update"], action)
    if action == "apt-install":
        verify_reference(cfg)
        validate_packages(args)
        return run(["/usr/bin/apt-get", "install", "-y", "--no-install-recommends", *args], action)
    if action == "apt-repair":
        verify_reference(cfg)
        rc = run(["/usr/bin/dpkg", "--configure", "-a"], "apt-repair-dpkg")
        if rc != 0:
            return rc
        return run(["/usr/bin/apt-get", "-f", "install", "-y"], "apt-repair-apt")
    if action == "service":
        if len(args) != 2:
            die("SERVICE_USAGE", 60)
        verb, unit = args
        if verb not in ALLOWED_SERVICE_ACTIONS or unit not in ALLOWED_UNITS:
            die("SERVICE_NOT_ALLOWED", 61)
        verify_reference(cfg)
        return run(["/usr/bin/systemctl", verb, unit], action)
    if action == "reboot":
        if args:
            die("REBOOT_TAKES_NO_ARGS", 70)
        reboot_guard(cfg)
        append_audit("reboot", [], "AUTHORIZED")
        subprocess.run(["/usr/bin/sync"], env=ENV, check=False)
        os.execve("/usr/bin/systemctl", ["/usr/bin/systemctl", "reboot"], ENV)
    if action == "revoke":
        if args:
            die("REVOKE_TAKES_NO_ARGS", 80)
        append_audit("revoke", [], "START")
        os.execve(str(REVOKE), [str(REVOKE), "manual"], ENV)

    die(f"ACTION_NOT_ALLOWED:{action}", 90)

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
