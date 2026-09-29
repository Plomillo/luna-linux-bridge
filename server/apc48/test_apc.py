#!/usr/bin/python3
import importlib.util
import pathlib

ROOT=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("apc", ROOT/"louksna_apc.py")
apc=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(apc)

good=[
    "curl",
    "python3",
    "libssl3:amd64",
    "pkg=1.2.3-1",
    "foo+bar",
    "linux-image-amd64",
]
bad=[
    "",
    "-o",
    "--option",
    "./evil.deb",
    "/tmp/evil.deb",
    "../../evil",
    "pkg;id",
    "pkg$(id)",
    "pkg name",
    "pkg|sh",
]
for p in good:
    assert apc.PKG_RE.fullmatch(p), p
for p in bad:
    assert not apc.PKG_RE.fullmatch(p), p

assert apc.ALLOWED_UNITS == {
    "louksna-r4-awake.service",
    "actions.runner.Plomillo-luna-linux-bridge.luna-linux.service",
}
assert "daemon-reload" not in apc.ALLOWED_SERVICE_ACTIONS
assert "cat" not in apc.ALLOWED_SERVICE_ACTIONS

activate=(ROOT/"activate-48h.sh").read_text(encoding="utf-8")
revoke=(ROOT/"louksna_apc_revoke.sh").read_text(encoding="utf-8")
helper=(ROOT/"louksna_apc.py").read_text(encoding="utf-8")

assert "NOPASSWD: ALL" not in activate
assert "NOTAFTER=" in activate
assert "PART1_POST_VALIDATION_PASS" in activate
assert "20260926T034746Z-38579" in activate
assert 'SERVER_READY_RUN="36503769931"' in activate
assert "PART_1_FULL_REINSTALL" in activate
assert "systemd-inhibit" in activate
assert "--why=LOUKSNA-R4-governed-installation-window" in activate
assert "--why=Governed R4 installation window" not in activate
assert "trap cleanup_on_exit EXIT" in activate
assert "RECOVERY_EVIDENCE=" in activate
assert "PREVIOUS_REVOKED_APC_RECOVERY=PASS" in activate
assert "ACTIVE_APC_ALREADY_PRESENT_NO_EXTENSION" in activate
assert "AWAKE_GUARD_NOT_STABLE" in activate
assert "AWAKE_GUARD_PID_CHANGED_DURING_STABILITY_WINDOW" in activate
assert '"schema":"LOUKSNA_R4_APC_AUTHORIZATION/2.0"' in activate
assert '"schema":"LOUKSNA_R4_APC_ACTIVATION_EVIDENCE/2.0"' in activate

assert "disable --now louksna-r4-apc-revoke.timer" in revoke
assert 'rm -f -- "$SUDOERS" "$HELPER" "$AWAKE_UNIT" "$REVOKE_SERVICE" "$REVOKE_TIMER"' in revoke
assert '"timer_disabled":True' in revoke

for forbidden in [
    "shell=True",
    "os.system(",
    "subprocess.Popen(",
    "/bin/sh",
    "/bin/bash",
    "eval(",
    "exec(",
]:
    assert forbidden not in helper, forbidden

print("APC48_V2_STATIC_TESTS=PASS")
