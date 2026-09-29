#!/usr/bin/python3
import importlib.util
import pathlib
import sys

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

text=(ROOT/"activate-48h.sh").read_text(encoding="utf-8")
assert "NOPASSWD: ALL" not in text
assert "NOTAFTER=" in text
assert "PART1_POST_VALIDATION_PASS" in text
assert "20260926T034746Z-38579" in text
assert "SERVER_READY_RUN=\"36503769931\"" in text
assert "PART_1_FULL_REINSTALL" in text
assert "systemd-inhibit" in text

helper=(ROOT/"louksna_apc.py").read_text(encoding="utf-8")
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

print("APC48_STATIC_TESTS=PASS")
