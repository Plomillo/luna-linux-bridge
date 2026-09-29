#!/usr/bin/python3
from __future__ import annotations
import argparse, hashlib, json, os, pathlib

EXPECTED_FILES = [
    "server/apc48/activate-48h.sh",
    "server/apc48/louksna_apc.py",
    "server/apc48/louksna_apc_revoke.sh",
    "server/apc48/test_apc.py",
]
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

    ui_path_bound = (
        "/home/diegoignacionorambuenamiranda/Descargas/LUNA_R4_UI_REFERENCE" in activate
        or (
            'OWNER_HOME="/home/$OWNER"' in activate
            and 'UI_REF="$OWNER_HOME/Descargas/LUNA_R4_UI_REFERENCE"' in activate
            and 'OWNER="diegoignacionorambuenamiranda"' in activate
        )
    )

    findings=[
        check("checkpoint_run_bound",CHECKPOINT_RUN in activate,CHECKPOINT_RUN),
        check("approved_ui_root_bound",ui_path_bound,"composed or literal exact UI root"),
        check("ui_image_hash_bound",IMAGE_SHA in activate,IMAGE_SHA),
        check("ui_kde_hash_bound",KDE_SHA in activate,KDE_SHA),
        check("server_ready_run_bound",SERVER_READY_RUN in activate,SERVER_READY_RUN),
        check("part1_resume","PART_1" in activate,"PART_1"),
        check("differential_resume","DIFFERENTIAL" in activate,"DIFFERENTIAL"),
        check("part2_gate","PART1_POST_VALIDATION_PASS" in activate,"PART1_POST_VALIDATION_PASS"),
        check("no_full_part1_reinstall","PART_1_FULL_REINSTALL" in activate,"explicitly prohibited"),
        check("hard_sudo_expiry","NOTAFTER=" in activate,"sudoers Date_Spec bound"),
        check("no_global_nopasswd","NOPASSWD: ALL" not in activate,"generic grant absent"),
        check("single_helper_scope","NOPASSWD: /usr/local/sbin/louksna-apc" in activate,"exact helper only"),
        check("sleep_idle_lid_inhibit","--what=sleep:idle:handle-lid-switch" in activate,"planned reboot remains available"),
        check("persistent_revocation_timer","OnCalendar=" in activate and "Persistent=true" in activate,"automatic expiry"),
        check("visudo_checks","visudo -cf" in activate and "visudo -c" in activate,"syntax validation"),
        check("bootstrap_rollback","rollback_on_error" in activate,"rollback trap present"),
        check("no_silent_extension","APC_ALREADY_ACTIVE_NO_EXTENSION" in activate,"window not silently extended"),
        check("service_allowlist","ALLOWED_UNITS = {AWAKE_UNIT, RUNNER_UNIT}" in helper,"two exact units"),
        check("package_option_rejection",'p.startswith("-")' in helper and '"/" in p' in helper,"path/option injection rejected"),
        check("reboot_rate_limit","len(history) >= 3" in helper and "7200" in helper,"3 per 2h"),
        check("revoke_removes_scope",'rm -f -- "$SUDOERS"' in revoke and "disable --now louksna-r4-awake.service" in revoke,"privilege + inhibit revoked"),
        check("negative_tests_present","APC48_STATIC_TESTS=PASS" in tests,"test marker"),
        check("no_canonical_mutation","Louksna.md" not in all_text and "LOUKSNAMEJORADA.md" not in all_text,"canonical files absent"),
        check("no_proyectos_scope_mutation","/PROYECTOS" not in all_text and "/Proyectos/" not in all_text,"protected project paths absent"),
        check("no_arbitrary_shell",all(x not in helper for x in ["shell=True","os.system(","/bin/sh","/bin/bash","eval(","exec("]),"no shell execution primitives"),
    ]
    ok=all(x["status"]=="PASS" for x in findings)
    out={
        "schema":"LOUKSNA_R4_APC48_G23/1.1",
        "status":"PASS" if ok else "FAIL",
        "candidate_digest_sha256":digest,
        "files":rows,
        "findings":findings,
        "independence":{
            "distinct_evaluator_identity":"TRUSTROOT_BRANCH_G23",
            "candidate_head_sha":os.environ.get("CANDIDATE_HEAD_SHA"),
            "validator_trust_root_sha":os.environ.get("GITHUB_WORKFLOW_SHA"),
            "candidate_code_executed":False,
            "candidate_consumed_as_data_only":True,
            "repair_allowed":False,
            "write_access_to_candidate":False
        },
        "scope":"PRE_INSTALLATION_CANDIDATE_STATIC_ASSURANCE",
        "runtime_host_activation_certified":False,
        "g24_allowed":ok
    }
    pathlib.Path(a.out).write_text(json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if ok else 3

if __name__=="__main__":
    raise SystemExit(main())
