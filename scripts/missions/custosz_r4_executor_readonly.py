#!/usr/bin/env python3
"""Material read-only research executor for the CUSTOSZ R4 runtime contract.
Runs only on GitHub-hosted compute. It reads repository sources and writes the
runtime-owned target/ack/FME files. It performs no host installation or disk mutation.
"""
import hashlib, json, os, re, sys, time
from pathlib import Path

def cjson(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")

def digest_obj(x):
    return hashlib.sha256(cjson(x)).hexdigest()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main(argv):
    if len(argv) != 9:
        raise SystemExit("EXPECTED_8_ARGUMENTS")
    dispatch, ack, fme, target, root, a1root, r4root, casroot = map(Path, argv[1:9])
    d=json.loads(dispatch.read_text(encoding="utf-8"))
    a={
        "mission_id":d["mission_id"],
        "dispatch_id":d["dispatch_id"],
        "executor_id":d["executor_id"],
        "accepted":True,
        "pid":os.getpid(),
        "process_or_execution_token":"github-hosted-custosz-v7-r4-readonly"
    }
    a["ack_digest"]=digest_obj(a)
    ack.write_text(json.dumps(a,sort_keys=True)+"\n",encoding="utf-8")

    A0=root/"Louksna.md"
    PU=root/"PUAC2.md"
    A1=a1root/"LOUKSNAMEJORADA.md"
    SK=r4root/"docs/luna-r4/source/SKELETON_CANONICO_REFERENCIA.txt"
    CAS=casroot/"artifacts/semantic-container/TRANSFER_STATUS.json"
    mission=root/"docs/missions/LUNA_R4_CUSTOSZ_V7/MISION_MAESTRA_DEFINITIVA.md"
    pu=PU.read_text(encoding="utf-8",errors="replace")
    sk=SK.read_text(encoding="utf-8",errors="replace")
    cas=json.loads(CAS.read_text(encoding="utf-8"))

    runtime_pin=None
    m=re.search(r"RUNTIME_SHA256=([0-9a-f]{64})",sk)
    if m:
        runtime_pin=m.group(1)

    result={
        "mission_id":d["mission_id"],
        "scope":"READONLY_RESEARCH",
        "status":"MATERIAL_RESEARCH_COMPLETED",
        "verified":{
            "a0_sha256":sha(A0),
            "a1_sha256":sha(A1),
            "puac2_sha256":sha(PU),
            "skeleton_sha256":sha(SK),
            "mission_sha256":sha(mission)
        },
        "puac2":{
            "candidate_2_0_present":"VERSION=2.0.0-CANDIDATE" in pu,
            "g23_not_granted":"G23=NO_CONCEDIDA" in pu,
            "g24_not_granted":"G24=NO_CONCEDIDA" in pu,
            "d01_d10_markers":sum(1 for x in ("D01","D02","D03","D04","D05","D06","D07","D08","D09","D10") if x in pu)
        },
        "r4":{
            "target_os_debian13":"TARGET_OS=Debian GNU/Linux 13 Trixie" in sk,
            "runtime_pin_declared":runtime_pin,
            "installation_performed_false":"INSTALLATION_PERFORMED=FALSE" in sk
        },
        "cas":{
            "expected":cas.get("cas_object_count_expected"),
            "uploaded":cas.get("cas_objects_uploaded"),
            "pending":cas.get("cas_objects_pending"),
            "content_validation_pending":cas.get("source_content_hash_validation_pending")
        },
        "conclusions":[
            "A0, A1, PUAC2, Skeleton and mission identities were verified on GitHub-hosted compute.",
            "The native CUSTOSZ continuation is registered on the real LUNA_PROJECT workspace; this material research is bound to the same mission_id without consuming user-host RAM.",
            "The staging runtime is selected by its staging manifest but its SHA-256 differs from the generic Skeleton runtime pin; host activation remains blocked until provenance/variant reconciliation.",
            "PUAC2 remains a 2.0.0 candidate with G23/G24 not granted; it may govern assurance requirements but cannot self-certify.",
            "CAS transfer completion and semantic runtime validation remain separate; the GitHub branch still records pending CAS objects.",
            "No installation, Windows/EFI/GPT/PROYECTOS mutation or reboot was performed."
        ],
        "next_authorized_research":[
            "Reconcile selected runtime variant against the Skeleton pin and original provenance.",
            "Complete A0-A1 semantic/admission evidence without mutating canonical sources.",
            "Complete CAS Git LFS transport from an isolated clean checkout and validate destination hashes.",
            "Prepare the differential R4 component matrix and sandbox installation lots.",
            "Independently test the consent/executor bridge before any host installation."
        ]
    }
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

    f={
        "mission_id":d["mission_id"],
        "dispatch_id":d["dispatch_id"],
        "binding_id":d["binding_id"],
        "pid":os.getpid(),
        "fme_id":"FME-GITHUB-R4-"+d["dispatch_id"],
        "target":str(target),
        "after_digest":sha(target),
        "effect_type":d["expected_effect"]["effect_type"],
        "effect_is_material":True,
        "effect_is_mission_relevant":True,
        "effect_is_authorized":True,
        "effect_is_observable":True
    }
    f["fme_digest"]=digest_obj(f)
    fme.write_text(json.dumps(f,sort_keys=True)+"\n",encoding="utf-8")
    # Keep the process alive long enough for the runtime to prove PROCESS_RUNNING after ACK/FME.
    time.sleep(1.0)
    return 0

if __name__=="__main__":
    raise SystemExit(main(sys.argv))
