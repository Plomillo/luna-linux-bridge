#!/usr/bin/python3
from __future__ import annotations
import argparse, hashlib, json, os, pathlib

EXPECTED_FILES = [
    "server/apc48/activate-48h.sh",
    "server/apc48/louksna_apc.py",
    "server/apc48/louksna_apc_revoke.sh",
    "server/apc48/test_apc.py",
]
EXPECTED_DIGEST = "ed3c4267f94b3c53f1fec64b331f72dc657ebcc5e2c62a9314321c67c89684b7"
CHECKPOINT_RUN = "20260926T034746Z-38579"
IMAGE_SHA = "8a9852c4155d64fd74059c7239e67c82e16e5acd556627d70575db85078d4ed4"
KDE_SHA = "c21e04d5447e123b59fc9b94d2e9684bc03ea164999ef6f60210e257557a16dc"
SERVER_READY_RUN = "36503769931"

def h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def check(name: str, ok: bool, detail: str) -> dict:
    return {"check":name,"status":"PASS" if ok else "FAIL","detail":detail}

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--candidate",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    root=pathlib.Path(a.candidate)

    rows=[]
    for rel in sorted(EXPECTED_FILES):
        q=root/rel
        if not q.is_file():
            raise SystemExit(f"MISSING_EXPECTED_FILE:{rel}")
        data=q.read_bytes()
        rows.append({"path":rel,"bytes":len(data),"sha256":h(data)})
    material="".join(f"{r['path']}\0{r['sha256']}\0{r['bytes']}\n" for r in rows).encode()
    digest=h(material)

    activate=(root/"server/apc48/activate-48h.sh").read_text(encoding="utf-8")
    helper=(root/"server/apc48/louksna_apc.py").read_text(encoding="utf-8")
    revoke=(root/"server/apc48/louksna_apc_revoke.sh").read_text(encoding="utf-8")
    tests=(root/"server/apc48/test_apc.py").read_text(encoding="utf-8")
    all_text=activate+helper+revoke+tests

    findings=[
        check("candidate_digest",digest==EXPECTED_DIGEST,EXPECTED_DIGEST),
        check("checkpoint_run_bound",CHECKPOINT_RUN in activate,CHECKPOINT_RUN),
        check("ui_image_hash_bound",IMAGE_SHA in activate,IMAGE_SHA),
        check("ui_kde_hash_bound",KDE_SHA in activate,KDE_SHA),
        check("server_ready_run_bound",SERVER_READY_RUN in activate,SERVER_READY_RUN),
        check("part1_differential","PART_1" in activate and "DIFFERENTIAL" in activate,"resume contract"),
        check("part2_gate","PART1_POST_VALIDATION_PASS" in activate,"gate preserved"),
        check("no_part0_repeat","PART_0" in activate,"explicitly prohibited by resume contract"),
        check("no_full_part1_reinstall","PART_1_FULL_REINSTALL" in activate,"explicitly prohibited"),
        check("awake_reason_regression_closed","--why=LOUKSNA-R4-governed-installation-window" in activate and "--why=Governed R4 installation window" not in activate,"single-token reason"),
        check("exit_trap_rollback","trap cleanup_on_exit EXIT" in activate,"explicit exits covered"),
        check("residual_recovery","PREVIOUS_REVOKED_APC_RECOVERY=PASS" in activate and "RECOVERY_EVIDENCE=" in activate,"previous revoked state preserved then cleaned"),
        check("active_no_extension","ACTIVE_APC_ALREADY_PRESENT_NO_EXTENSION" in activate,"active APC not overwritten"),
        check("timer_cleanup_before_reinstall","disable --now louksna-r4-apc-revoke.timer" in activate,"residual timer removed before reinstall"),
        check("awake_stability_window","AWAKE_GUARD_NOT_STABLE" in activate and "AWAKE_GUARD_PID_CHANGED_DURING_STABILITY_WINDOW" in activate,"post-start stability check"),
        check("authorization_schema_v2",'LOUKSNA_R4_APC_AUTHORIZATION/2.0' in activate,"schema 2.0"),
        check("activation_evidence_schema_v2",'LOUKSNA_R4_APC_ACTIVATION_EVIDENCE/2.0' in activate,"schema 2.0"),
        check("hard_sudo_expiry","NOTAFTER=" in activate,"hard UTC bound"),
        check("no_global_nopasswd","NOPASSWD: ALL" not in activate,"generic grant absent"),
        check("single_helper_scope","NOPASSWD: /usr/local/sbin/louksna-apc" in activate,"exact helper only"),
        check("revoker_stops_timer","disable --now louksna-r4-apc-revoke.timer" in revoke,"timer disabled"),
        check("revoker_removes_surface",'rm -f -- "$SUDOERS" "$HELPER" "$AWAKE_UNIT" "$REVOKE_SERVICE" "$REVOKE_TIMER"' in revoke,"privileged surface removed"),
        check("service_allowlist","ALLOWED_UNITS = {AWAKE_UNIT, RUNNER_UNIT}" in helper,"two exact units"),
        check("package_option_rejection",'p.startswith("-")' in helper and '"/" in p' in helper,"path/option injection rejected"),
        check("reboot_rate_limit","len(history) >= 3" in helper and "7200" in helper,"3 per 2h"),
        check("tests_regression_marker","APC48_V2_STATIC_TESTS=PASS" in tests,"v2 regression tests"),
        check("no_canonical_mutation","Louksna.md" not in all_text and "LOUKSNAMEJORADA.md" not in all_text,"canonical files absent"),
        check("no_proyectos_scope_mutation","/PROYECTOS" not in all_text and "/Proyectos/" not in all_text,"protected project paths absent"),
        check("no_arbitrary_shell",all(x not in helper for x in ["shell=True","os.system(","/bin/sh","/bin/bash","eval(","exec("]),"no arbitrary shell primitives"),
    ]
    ok=all(x["status"]=="PASS" for x in findings)
    out={
        "schema":"LOUKSNA_R4_APC48_V2_G23/1.0",
        "status":"PASS" if ok else "FAIL",
        "candidate_digest_sha256":digest,
        "files":rows,
        "findings":findings,
        "independence":{
            "distinct_evaluator_identity":"APC48_V2_TRUSTROOT_G23",
            "candidate_head_sha":os.environ.get("CANDIDATE_HEAD_SHA"),
            "validator_trust_root_sha":os.environ.get("GITHUB_WORKFLOW_SHA"),
            "candidate_code_executed":False,
            "candidate_consumed_as_data_only":True,
            "repair_allowed":False,
            "write_access_to_candidate":False
        },
        "incident_regressions_closed":[
            "AWAKE_GUARD_WHY_ARGUMENT_SPLIT",
            "FAIL_EXIT_BYPASSED_ERR_TRAP",
            "RESIDUAL_REVOKE_TIMER",
            "INCOMPLETE_BOOTSTRAP_RECOVERY"
        ],
        "scope":"PRE_INSTALLATION_CANDIDATE_STATIC_ASSURANCE_V2",
        "runtime_host_activation_certified":False,
        "g24_allowed":ok
    }
    pathlib.Path(a.out).write_text(json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if ok else 3

if __name__=="__main__":
    raise SystemExit(main())
