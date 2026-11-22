#!/usr/bin/env python3
"""Luna operational agent.

It runs commands and records raw output. It does not train weights, does not
invent evidence, and does not certify the product.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def manifest() -> dict:
    return {
        "name": "luna-metaagent",
        "kind": "executable-policy",
        "weight_training": "NOT_AUTHORIZED",
        "consciousness": "NOT_CLAIMED",
        "product_platform": "NOT_CERTIFIED",
        "self_certifies": False,
        "runs_historical_36": False,
        "reruns_original_803": False,
    }


def run_command(argv: list[str], env: dict | None = None, timeout: int = 180) -> dict:
    proc = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=timeout)
    return {
        "argv": argv,
        "code": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }


def judge(expect: str, result: dict, needle: str = "", expect_code: int | None = None) -> bool:
    code = result["code"]
    out = result["stdout"] or ""
    if expect == "code0":
        return code == 0
    if expect == "code_eq":
        return code == expect_code
    if expect == "stdout_contains":
        return code == 0 and needle in out
    if expect == "stdout_eq":
        return code == 0 and out.strip() == needle
    if expect == "any_line_eq":
        return code == 0 and needle in {line.strip() for line in out.splitlines()}
    if expect == "json_selftest":
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return False
        return code == 0 and data.get("ok") is True and data.get("certification") == "NOT_CERTIFIED"
    if expect == "json_luna":
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return False
        return (
            code == 0
            and data.get("weight_training") == "NOT_AUTHORIZED"
            and data.get("consciousness") == "NOT_CLAIMED"
            and data.get("product_platform") == "NOT_CERTIFIED"
            and data.get("self_certifies") is False
        )
    return False


CASES = [
    ("SUB-001", "Debian 13 VERSION_ID", ["bash", "-lc", "grep -E '^VERSION_ID=' /etc/os-release"], "stdout_contains", 'VERSION_ID="13"'),
    ("SUB-002", "PID 1 is systemd", ["bash", "-lc", "tr -d '\\0' </proc/1/comm"], "stdout_eq", "systemd"),
    ("SUB-003", "systemctl is-system-running is running", ["systemctl", "is-system-running"], "stdout_eq", "running"),
    ("SUB-004", "test user is not root", ["bash", "-lc", "u=$(id -u louksna); test \"$u\" -gt 0 && echo NONROOT"], "stdout_eq", "NONROOT"),
    ("SUB-005", "os id debian", ["bash", "-lc", "grep -E '^ID=' /etc/os-release"], "stdout_eq", "ID=debian"),
    ("SUB-006", "louksna package configured", ["bash", "-lc", "dpkg-query -W -f '${db:Status-Status}\\n' louksna"], "stdout_eq", "installed"),
    ("SUB-007", "session binary is ELF", ["bash", "-lc", "od -An -t x1 -N 4 /usr/bin/louksna-session"], "stdout_contains", "7f 45 4c 46"),
    ("SUB-008", "sh prefix binary exists", ["bash", "-lc", "test -x /opt/louksna-sh/usr/bin/louksna-session && echo PRESENT"], "stdout_eq", "PRESENT"),
    ("SUB-009", "install log has no force-depends", ["bash", "-lc", "if grep -q -- '--force-depends' /var/log/louksna-dpkg.log; then echo USED; else echo ABSENT; fi"], "stdout_eq", "ABSENT"),
    ("SUB-010", "selftest ok and not product-certified", ["bash", "-lc", "/usr/bin/louksna-session --selftest"], "json_selftest", ""),
    ("SUB-011", "speak writes a wav", ["bash", "-lc", "wav=$(/usr/bin/louksna-session --state /var/tmp/louksna-voice --speak 'Hola. Soy Luna.'); test -s \"$wav\" && echo RIFF_OK"], "stdout_eq", "RIFF_OK"),
    ("SUB-012", "stt hears luna", ["bash", "-lc", "wav=$(/usr/bin/louksna-session --state /var/tmp/louksna-voice --speak 'Hola. Soy Luna.'); /usr/bin/louksna-session --state /var/tmp/louksna-voice --transcribe \"$wav\""], "stdout_contains", "una"),
    ("SUB-013", "launcher without wayland exits 3", ["bash", "-lc", "env -u WAYLAND_DISPLAY XDG_SESSION_TYPE=tty /usr/bin/louksna-launch; echo RC:$?"], "stdout_contains", "RC:3"),
    ("SUB-014", "plasmashell binary", ["bash", "-lc", "test -x /usr/bin/plasmashell && echo PRESENT"], "stdout_eq", "PRESENT"),
    ("SUB-015", "startplasma-wayland binary", ["bash", "-lc", "test -x /usr/bin/startplasma-wayland && echo PRESENT"], "stdout_eq", "PRESENT"),
    ("SUB-016", "sddm active", ["systemctl", "is-active", "sddm"], "stdout_eq", "active"),
    ("SUB-017", "loginctl wayland session", ["bash", "-lc", "loginctl list-sessions --no-legend | awk '{print $1}' | while read -r s; do loginctl show-session \"$s\" -p Name -p Type -p State; done"], "stdout_contains", "Type=wayland"),
    ("SUB-018", "wayland socket", ["bash", "-lc", "uid=$(id -u louksna); find /run/user/$uid -maxdepth 1 -type s -name 'wayland-*' | head -n 1"], "stdout_contains", "wayland-"),
    ("SUB-019", "kwin process", ["bash", "-lc", "if pgrep -a -f 'kwin_wayland|kwin' >/dev/null; then echo KWIN; else echo ABSENT; fi"], "stdout_eq", "KWIN"),
    ("SUB-020", "plasmashell process", ["bash", "-lc", "if pgrep -x plasmashell >/dev/null; then echo PLASMA; else echo ABSENT; fi"], "stdout_eq", "PLASMA"),
    ("SUB-021", "virtual drm node", ["bash", "-lc", "ls /dev/dri 2>/dev/null || true"], "stdout_contains", "card"),
    ("SUB-022", "snd node", ["bash", "-lc", "if [ -d /dev/snd ]; then echo SND; else echo ABSENT; fi"], "stdout_eq", "SND"),
    ("SUB-023", "pactl info", ["bash", "-lc", "if command -v pactl >/dev/null; then pactl info; else echo ABSENT; exit 1; fi"], "code0", ""),
    ("SUB-024", "posix acl roundtrip", ["bash", "-lc", "f=/var/tmp/louksna-acl; echo x > \"$f\"; setfacl -m u:nobody:r \"$f\"; getfacl -c \"$f\""], "stdout_contains", "user:nobody:r"),
    ("SUB-025", "llvm-as and opt", ["bash", "-lc", "d=/var/tmp/ll; mkdir -p \"$d\"; printf 'define i32 @add(i32 %%a, i32 %%b) {\\n  %%c = add i32 %%a, %%b\\n  ret i32 %%c\\n}\\n' > \"$d/a.ll\"; llvm-as \"$d/a.ll\" -o \"$d/a.bc\"; opt -S \"$d/a.bc\" -o \"$d/a.opt.ll\"; grep -c 'define i32 @add' \"$d/a.opt.ll\""], "stdout_eq", "1"),
    ("SUB-026", "unshare user", ["unshare", "--user", "--map-root-user", "true"], "code0", ""),
    ("SUB-027", "unshare net", ["unshare", "--net", "true"], "code0", ""),
    ("SUB-028", "pid1 namespace readable", ["bash", "-lc", "readlink /proc/1/ns/pid"], "code0", ""),
    ("SUB-029", "journalctl reads", ["journalctl", "-n", "1", "--no-pager"], "code0", ""),
    ("SUB-030", "apt indexes", ["apt-get", "update"], "code0", ""),
    ("SUB-031", "network to debian", ["ping", "-c", "1", "-W", "8", "deb.debian.org"], "code0", ""),
    ("SUB-032", "python3 present", ["python3", "--version"], "stdout_contains", "Python 3"),
    ("SUB-033", "root fs at least 3G", ["bash", "-lc", "kb=$(df -Pk / | awk 'NR==2{print $4}'); test \"$kb\" -ge 3000000 && echo BIG"], "stdout_eq", "BIG"),
    ("SUB-034", "guest virtualization visible", ["bash", "-lc", "v=$(systemd-detect-virt || true); if [ -n \"$v\" ] && [ \"$v\" != none ]; then echo VIRT:$v; exit 0; fi; if grep -q hypervisor /proc/cpuinfo; then echo VIRT:hypervisor; exit 0; fi; echo VIRT:none; exit 1"], "stdout_contains", "VIRT:"),
    ("SUB-035", "mesa dri package", ["bash", "-lc", "dpkg-query -W -f '${Status}\\n' libgl1-mesa-dri"], "stdout_contains", "install ok installed"),
    ("SUB-036", "xdg desktop portal", ["bash", "-lc", "if pgrep -f xdg-desktop-portal >/dev/null || systemctl is-active --quiet xdg-desktop-portal; then echo PORTAL; else echo ABSENT; fi"], "stdout_eq", "PORTAL"),
    ("SUB-037", "kde portal", ["bash", "-lc", "if pgrep -f xdg-desktop-portal-kde >/dev/null; then echo KDEPORTAL; else echo ABSENT; fi"], "stdout_eq", "KDEPORTAL"),
    ("SUB-038", "pipewire or pulse", ["bash", "-lc", "if pgrep -x pipewire >/dev/null || pgrep -x pulseaudio >/dev/null; then echo AUDIO_SERVER; else echo ABSENT; fi"], "stdout_eq", "AUDIO_SERVER"),
    ("SUB-039", "louksna in audio group", ["bash", "-lc", "id louksna"], "stdout_contains", "audio"),
    ("SUB-040", "uname linux", ["uname", "-s"], "stdout_eq", "Linux"),
    ("SUB-041", "kernel cmdline", ["bash", "-lc", "test -s /proc/cmdline && echo CMDLINE"], "stdout_eq", "CMDLINE"),
    ("SUB-042", "marker survived reboot", ["bash", "-lc", "test \"$(cat /var/lib/louksna-boot-marker)\" = phase-a && echo KEPT"], "stdout_eq", "KEPT"),
    ("SUB-043", "sh and deb session hashes match", ["bash", "-lc", "a=$(sha256sum /usr/bin/louksna-session | awk '{print $1}'); b=$(sha256sum /opt/louksna-sh/usr/bin/louksna-session | awk '{print $1}'); if [ \"$a\" = \"$b\" ]; then echo MATCH; else echo DIFFER; fi"], "stdout_eq", "MATCH"),
    ("SUB-044", "sh reinstall keeps hash", ["bash", "-lc", "h1=$(sha256sum /opt/louksna-sh/usr/bin/louksna-session | awk '{print $1}'); sh /var/tmp/LOUKSNA.sh --prefix /opt/louksna-sh --uninstall; sh /var/tmp/LOUKSNA.sh --prefix /opt/louksna-sh; h2=$(sha256sum /opt/louksna-sh/usr/bin/louksna-session | awk '{print $1}'); if [ \"$h1\" = \"$h2\" ]; then echo RESTORED; else echo CHANGED; fi"], "stdout_eq", "RESTORED"),
    ("SUB-045", "dpkg remove and reinstall without force-depends", ["bash", "-lc", "dpkg -r louksna && apt-get install -y libgomp1 libstdc++6 ca-certificates && dpkg -i /var/tmp/LOUKSNA.deb && dpkg-query -W -f '${db:Status-Status}\\n' louksna"], "stdout_eq", "installed"),
    ("SUB-046", "selftest after reinstall", ["bash", "-lc", "/usr/bin/louksna-session --selftest"], "json_selftest", ""),
    ("SUB-047", "luna manifest refuses self-certification", ["bash", "-lc", "python3 /var/tmp/luna-agent.py --manifest"], "json_luna", ""),
    ("SUB-048", "a failing command stays failed", ["bash", "-lc", "python3 /var/tmp/luna-agent.py --probe-false"], "stdout_eq", "FAIL"),
    ("SUB-049", "checker did not export a fake wayland display", ["bash", "-lc", "if [ -n \"${LOUKSNA_FAKE_WAYLAND:-}\" ]; then echo FAKE; else echo CLEAN; fi"], "stdout_eq", "CLEAN"),
    ("SUB-050", "wayland socket still present at end", ["bash", "-lc", "uid=$(id -u louksna); n=$(find /run/user/$uid -maxdepth 1 -type s -name 'wayland-*' | wc -l); test \"$n\" -ge 1 && echo STILL"], "stdout_eq", "STILL"),
    ("SUB-051", "original c375 inside plasma environment", ["bash", "-lc", "python3 /var/tmp/probe_original.py 375"], "stdout_contains", "PASS_FUNCTIONAL"),
    ("SUB-052", "original c376 inside plasma environment", ["bash", "-lc", "python3 /var/tmp/probe_original.py 376"], "stdout_contains", "PASS_FUNCTIONAL"),
    ("SUB-053", "original c379 audio probe", ["bash", "-lc", "python3 /var/tmp/probe_original.py 379"], "stdout_contains", "PASS_FUNCTIONAL"),
]


def execute(out_dir: Path) -> list[dict]:
    results = []
    env = os.environ.copy()
    env.pop("LOUKSNA_FAKE_WAYLAND", None)
    env.setdefault("LOUKSNA_REQUIRE_SYNTHESIS", "1")
    for sid, title, argv, expect, needle in CASES:
        try:
            raw = run_command(argv, env=env, timeout=300)
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            raw = {"argv": argv, "code": 127, "stdout": "", "stderr": str(exc)[:400]}
        passed = judge(expect, raw, needle)
        results.append({
            "id": sid,
            "title": title,
            "expect": expect,
            "needle": needle,
            "argv": raw["argv"],
            "code": raw["code"],
            "stdout": raw["stdout"],
            "stderr": raw["stderr"],
            "pass": passed,
        })
        print(f"{sid} {'PASS' if passed else 'FAIL'}", flush=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "agent-53-case-execution.json").write_text(json.dumps(results, indent=2) + "\n")
    (out_dir / "agent-manifest.json").write_text(json.dumps(manifest(), indent=2) + "\n")
    return results


def main() -> int:
    if "--manifest" in sys.argv:
        print(json.dumps(manifest()))
        return 0
    if "--probe-false" in sys.argv:
        raw = run_command(["false"])
        print("FAIL" if not judge("code0", raw) else "PASS")
        return 0
    out = Path(sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--out" else "/var/tmp/luna-out")
    execute(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
