#!/usr/bin/env python3
"""Read-only reconciliation of LOUKSNA's existing APC v1.2.1, never an authority grant."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

import lrb_core as base

APC = Path("/usr/local/sbin/louksna-apc")
RUNUSER = Path("/usr/sbin/runuser")
SCHEMA = "LRB_EXISTING_APC_READONLY_PROBE/0.3"
HASH = re.compile(r"^[0-9a-f]{64}$")
DEFAULT_MANIFEST = Path("mission-control/privilege-bridge/V121-CERTIFIED-20260930T033205Z.json")


def sha(path, limit=5 * 1024 * 1024):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise RuntimeError("SOURCE_PATH_UNSAFE_OR_UNBOUNDED")
    h = hashlib.sha256()
    with path.open("rb") as file:
        while data := file.read(65536):
            h.update(data)
    return h.hexdigest()


def parse_hash_output(stdout, path):
    match = stdout.decode("utf8","replace").strip().splitlines()
    if len(match) != 1:
        raise RuntimeError("AMBIGUOUS_SUDO_SHA256_OUTPUT")
    found = match[0].split(maxsplit=1)
    if len(found) != 2 or not HASH.fullmatch(found[0]) or found[1].lstrip("*") != str(path):
        raise RuntimeError("SUDO_SHA256_OUTPUT_UNBOUND")
    return found[0]


def privileged_readonly_sha(path, invoke=subprocess.run):
    # Only the known exact certificate pathname from the historic manifest is
    # admitted. No shell expansion, arguments from the mission or sudo bash.
    try:
        proc = invoke(["sudo","-n","/usr/bin/sha256sum",str(path)],
                      stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                      stderr=subprocess.PIPE,timeout=5,check=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise RuntimeError("FIXED_SCOPE_ROOT_READ_UNAVAILABLE") from exc
    if proc.returncode != 0:
        raise RuntimeError("SUDO_FIXED_SHA256_NOT_ALLOWED")
    return parse_hash_output(proc.stdout,path)


def collect(manifest, host="LOUKSNA", invoke=subprocess.run, apc=APC, runuser=RUNUSER):
    if (manifest.get("schema") != "LOUKSNA_PRIVILEGE_BRIDGE_SYNC/1.0"
            or manifest.get("bridge",{}).get("version") != "1.2.1"
            or manifest.get("status") != "PASS_STRICT"
            or manifest.get("host") != host):
        raise RuntimeError("HISTORIC_PRIVILEGE_RECORD_INVALID")
    if os.uname().nodename != host or os.geteuid() == 0:
        raise RuntimeError("UNEXPECTED_HOST_OR_ROOT_RUNNER_DENIED")
    runuser_expected = manifest["runuser"]["sha256"]
    if not HASH.fullmatch(runuser_expected) or sha(runuser) != runuser_expected:
        raise RuntimeError("CURRENT_RUNUSER_BINARY_HASH_MISMATCH")
    if apc.is_symlink() or not apc.is_file():
        raise RuntimeError("EXISTING_APC_BINARY_MISSING")
    metadata=apc.stat()
    if metadata.st_uid != 0 or metadata.st_mode & 0o022 or not metadata.st_mode & stat.S_IXUSR:
        raise RuntimeError("EXISTING_APC_OWNERSHIP_OR_MODE_UNSAFE")
    try:
        check=invoke(["sudo","-n","true"],stdin=subprocess.DEVNULL,
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=3,check=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise RuntimeError("CURRENT_NONINTERACTIVE_SUDO_UNAVAILABLE") from exc
    if check.returncode != 0:
        raise RuntimeError("CURRENT_NONINTERACTIVE_SUDO_UNAVAILABLE")
    history=manifest["bridge"]
    matches={}
    for role in ("g23","g24"):
        path=Path(history[role+"_path"])
        expected=history[role+"_sha256"]
        if not HASH.fullmatch(expected) or not path.is_absolute():
            raise RuntimeError("UNSAFE_HISTORICAL_CERTIFICATE_REFERENCE")
        measured=privileged_readonly_sha(path,invoke)
        if measured != expected:
            raise RuntimeError("HISTORICAL_CERTIFICATE_HASH_CHANGED_"+role.upper())
        matches[role]={"path":str(path),"sha256":measured,
                       "historical_digest_reverified":True,
                       "new_lrb_gate":"NOT_ISSUED"}
    binary_sha = sha(apc)
    return {"schema":SCHEMA,"status":"HISTORICAL_COMPONENT_IDENTITIES_MATCH_NOT_LRB_CERTIFIED",
            "host":host,"runuser_sha256":runuser_expected,
            "apc_sha256_observed_not_pinned_by_historic_record":binary_sha,
            "apc_owner_uid":metadata.st_uid,
            "apc_mode":format(stat.S_IMODE(metadata.st_mode),"04o"),
            "sudo_noninteractive":"AVAILABLE_CHECK_ONLY",
            "historic_certificates":matches,
            "sudo_policy_full_sha256":"NOT_LIVE_VERIFIED",
            "g23_current_lrb":"NOT_EXECUTED","g24_current_lrb":"NOT_EXECUTED",
            "g23_2_current_lrb":"NOT_EXECUTED","g24_2_current_lrb":"NOT_EXECUTED",
            "root_mutation_authorized":False,"certified":False}


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",default=str(DEFAULT_MANIFEST))
    parser.add_argument("--out",required=True)
    args=parser.parse_args(argv)
    try:
        manifestpath=Path(args.manifest)
        if manifestpath.is_symlink() or not manifestpath.is_file() or manifestpath.stat().st_size > 32768:
            raise RuntimeError("MANIFEST_UNSAFE")
        data=json.loads(manifestpath.read_text(encoding="utf8"))
        report=collect(data)
        base.atomic_json(Path(args.out),report)
        print(json.dumps(report,sort_keys=True))
        return 0
    except Exception as exc:
        report={"schema":SCHEMA,"status":"HOLD","reason":str(exc)[:150],
                "root_mutation_authorized":False,"certified":False}
        base.atomic_json(Path(args.out),report)
        print(json.dumps(report,sort_keys=True),file=sys.stderr)
        return 3


if __name__=="__main__":
    sys.exit(main())
