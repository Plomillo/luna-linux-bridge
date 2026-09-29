#!/usr/bin/python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys

EXPECTED_FILES = {
    "server/apc48/louksna_apc.py",
    "server/apc48/louksna_apc_revoke.sh",
    "server/apc48/activate-48h.sh",
    "server/apc48/test_apc.py",
}

CHECKPOINT = "/home/diegoignacionorambuenamiranda/LOUKSNA_MAESTRO_20260925/MISSION3_OPERATIVE/R4_PART1_DESKTOP_V1/runs/20260926T034746Z-38579"
UI_ROOT = "/home/diegoignacionorambuenamiranda/Descargas/LUNA_R4_UI_REFERENCE"
IMAGE_SHA = "8a9852c4155d64fd74059c7239e67c82e16e5acd556627d70575db85078d4ed4"
KDE_SHA = "c21e04d5447e123b59fc9b94d2e9684bc03ea164999ef6f60210e257557a16dc"
SERVER_READY_RUN = "36503769931"

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def freeze_digest(candidate: pathlib.Path) -> tuple[str, list[dict]]:
    rows = []
    for rel in sorted(EXPECTED_FILES):
        p = candidate / rel
        if not p.is_file():
            raise SystemExit(f"MISSING_EXPECTED_FILE:{rel}")
        data = p.read_bytes()
        rows.append({"path": rel, "bytes": len(data), "sha256": sha256_bytes(data)})
    material = "".join(f"{r['path']}\0{r['sha256']}\0{r['bytes']}\n" for r in rows).encode()
    return sha256_bytes(material), rows

def finding(check: str, ok: bool, detail: str) -> dict:
    return {"check": check, "status": "PASS" if ok else "FAIL", "detail": detail}

def g23(args: argparse.Namespace) -> int:
    candidate = pathlib.Path(args.candidate)
    digest, rows = freeze_digest(candidate)
    a = (candidate / "server/apc48/activate-48h.sh").read_text(encoding="utf-8", errors="strict")
    h = (candidate / "server/apc48/louksna_apc.py").read_text(encoding="utf-8", errors="strict")
    r = (candidate / "server/apc48/louksna_apc_revoke.sh").read_text(encoding="utf-8", errors="strict")
    t = (candidate / "server/apc48/test_apc.py").read_text(encoding="utf-8", errors="strict")

    findings = []
    findings += [
        finding("exact_checkpoint_bound", CHECKPOINT in a, CHECKPOINT),
        finding("approved_ui_root_bound", UI_ROOT in a, UI_ROOT),
        finding("ui_image_hash_bound", IMAGE_SHA in a, IMAGE_SHA),
        finding("ui_kde_hash_bound", KDE_SHA in a, KDE_SHA),
        finding("server_ready_run_bound", SERVER_READY_RUN in a, SERVER_READY_RUN),
        finding("resume_part1", 'START_PART=PART_1' in a or '"start_part":"PART_1"' in a, "PART_1"),
        finding("differential_resume", "DIFFERENTIAL" in a, "DIFFERENTIAL"),
        finding("part2_gate", "PART1_POST_VALIDATION_PASS" in a, "PART1_POST_VALIDATION_PASS"),
        finding("no_full_reinstall", "PART_1_FULL_REINSTALL" in a, "explicitly prohibited"),
        finding("sudoers_notafter", "NOTAFTER=" in a, "hard UTC expiration"),
        finding("no_nopasswd_all", "NOPASSWD: ALL" not in a, "generic root grant absent"),
        finding("single_helper_sudo_scope", "NOPASSWD: /usr/local/sbin/louksna-apc" in a, "exact helper only"),
        finding("sleep_inhibitor", "systemd-inhibit" in a and "--what=sleep:idle:handle-lid-switch" in a, "planned reboot remains possible"),
        finding("absolute_revoke_timer", "OnCalendar=" in a and "Persistent=true" in a, "persistent timer"),
        finding("root_helper_hash_verification", "HELPER_INSTALL_HASH_MISMATCH" in a, "post-install identity check"),
        finding("revoke_hash_verification", "REVOKE_INSTALL_HASH_MISMATCH" in a, "post-install identity check"),
        finding("visudo_validation", "/usr/sbin/visudo -cf" in a and "/usr/sbin/visudo -c" in a, "syntax + global validation"),
        finding("rollback_on_error", "rollback_on_error" in a and "trap rollback_on_error ERR INT TERM" in a, "bootstrap rollback"),
        finding("no_silent_extension", "APC_ALREADY_ACTIVE_NO_EXTENSION" in a, "active window not silently extended"),
        finding("password_not_stored", '"password_stored":False' in a, "evidence claim matches design"),
        finding("no_arbitrary_shell_helper", all(x not in h for x in ["shell=True","os.system(","/bin/sh","/bin/bash","eval(","exec("]), "no shell execution primitives"),
        finding("service_allowlist", "ALLOWED_UNITS = {AWAKE_UNIT, RUNNER_UNIT}" in h, "exact unit allowlist"),
        finding("package_path_rejected", '"/" in p' in h and 'p.startswith("-")' in h, "local deb/path and option injection rejected"),
        finding("configured_repo_only", '["/usr/bin/apt-get", "install", "-y", "--no-install-recommends", *args]' in h, "apt package names only"),
        finding("reboot_rate_limit", "len(history) >= 3" in h and "7200" in h, "max three / two hours"),
        finding("reference_reverify_before_privileged_ops", h.count("verify_reference(cfg)") >= 4, "reference/checkpoint rebound before mutation"),
        finding("revoke_removes_sudoers", 'rm -f -- "$SUDOERS"' in r, "privilege removal"),
        finding("revoke_stops_awake_guard", "disable --now louksna-r4-awake.service" in r, "power policy restored"),
        finding("candidate_tests_present", "APC48_STATIC_TESTS=PASS" in t, "negative/static test suite"),
        finding("no_canonical_file_mutation", "Louksna.md" not in a+h+r+t and "LOUKSNAMEJORADA.md" not in a+h+r+t, "canonical authority untouched"),
        finding("no_projects_scope_mutation", "/PROYECTOS" not in a+h+r+t and "/Proyectos/" not in a+h+r+t, "protected project scope not targeted"),
    ]

    independence = {
        "distinct_evaluator_identity": "BASE_BRANCH_PULL_REQUEST_TARGET_G23",
        "candidate_code_executed": False,
        "candidate_consumed_as_data_only": True,
        "repair_allowed": False,
        "write_access_to_candidate": False,
        "validator_trust_root_sha": os.environ.get("GITHUB_WORKFLOW_SHA"),
        "candidate_head_sha": os.environ.get("CANDIDATE_HEAD_SHA"),
    }
    ok = all(x["status"] == "PASS" for x in findings)
    out = {
        "schema": "LOUKSNA_R4_APC48_G23/1.0",
        "status": "PASS" if ok else "FAIL",
        "candidate_digest_sha256": digest,
        "files": rows,
        "findings": findings,
        "independence": independence,
        "scope": "PRE_INSTALLATION_CANDIDATE_STATIC_ASSURANCE",
        "runtime_host_activation_certified": False,
        "g24_allowed": ok,
    }
    pathlib.Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if ok else 3

def g24(args: argparse.Namespace) -> int:
    g23 = json.loads(pathlib.Path(args.g23).read_text(encoding="utf-8"))
    authority = json.loads(pathlib.Path(args.authority).read_text(encoding="utf-8"))
    if g23.get("status") != "PASS":
        raise SystemExit("G23_NOT_PASS")
    if not authority.get("authority_authenticated"):
        raise SystemExit("AUTHORITY_NOT_AUTHENTICATED")
    digest = g23["candidate_digest_sha256"]
    if authority.get("candidate_digest_sha256") != digest:
        raise SystemExit("DIGEST_BINDING_MISMATCH")
    cert = {
        "schema": "LOUKSNA_R4_APC48_G24/1.0",
        "status": "PASS",
        "certificate_scope": "PRE_INSTALLATION_CANDIDATE_ONLY",
        "candidate_digest_sha256": digest,
        "g23_status": "PASS",
        "authority_authenticated": True,
        "authority_reference": authority.get("signature_reference"),
        "candidate_head_sha": authority.get("candidate_head_sha"),
        "validator_trust_root_sha": authority.get("trust_root_sha"),
        "canonical_mutation": False,
        "authority_transfer": False,
        "runtime_host_activation_certified": False,
        "post_installation_certificate_required": True,
    }
    pathlib.Path(args.out).write_text(json.dumps(cert, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(cert, ensure_ascii=False, indent=2))
    return 0

def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("g23")
    a.add_argument("--candidate", required=True)
    a.add_argument("--out", required=True)
    b = sub.add_parser("g24")
    b.add_argument("--g23", required=True)
    b.add_argument("--authority", required=True)
    b.add_argument("--out", required=True)
    args = p.parse_args()
    return g23(args) if args.cmd == "g23" else g24(args)

if __name__ == "__main__":
    raise SystemExit(main())
