#!/usr/bin/env python3
"""Deterministic metacognitive mission diagnosis, bounded and non-mutating.

Not an LLM or a universal task executor: it converts the live, verified state
of the existing automation into one exact next route without changing authority.
"""
from __future__ import annotations
from datetime import datetime, timezone
import copy
import json
from pathlib import Path
import sys

import lrb_core as base
import elastic_automation as elastic

SCHEMA="LRB_METACOGNITIVE_DIAGNOSTIC/0.3"


def diagnose(automation, mission_id, observation=None, same_uid_socket_verified=False,
             github_runner_live_verified=False):
    """All mutable action remains in the bounded Scheduler or independent governor."""
    if not isinstance(mission_id,str) or not elastic.MID.fullmatch(mission_id):
        raise RuntimeError("MISSION_ID_INVALID")
    with automation.exclusive() as commits:
        document=automation.read(commits)
        if mission_id not in document["missions"]:
            raise RuntimeError("MISSION_UNKNOWN")
        row=copy.deepcopy(document["missions"][mission_id])
        chain=automation.ledger.verify()
        policy=base.load_time_policy(automation.state,automation.contract)
    mission=row["request"]
    elastic.validate(mission,policy)
    now=automation.clock()
    obs=observation if observation is not None else automation.observer()
    resource=elastic.Automation.resource_guard(obs)
    steps=mission["steps"]
    idx=row["next_step"]
    audit={
        "owner_goal_exact":mission["user_objective"],
        "llm_proposal_separate":mission["model_proposal"],
        "model_self_declared":mission["model"],
        "model_provider_attestation":"NOT_AVAILABLE",
        "mission_sha256":row["mission_sha256"],
        "evidence_chain_head":chain,
        "g23":"NOT_EXECUTED","g24":"NOT_EXECUTED",
        "g23_2":"NOT_EXECUTED","g24_2":"NOT_EXECUTED",
        "certified":False,"privileged_execution_allowed":False
    }
    channel={
        "local_same_uid_live_socket":"VERIFIED_IN_PROCESS" if same_uid_socket_verified else "UNKNOWN",
        "github_runner":"LIVE_VERIFIED_EXTERNAL" if github_runner_live_verified else "HISTORIC_PROOFS_NOT_LIVE",
        "remote_screen":"NOT_AVAILABLE",
        "remote_root":"NOT_AVAILABLE"
    }
    routes=[]
    blockers=[]
    if row["status"]=="WAITING_FRESH_G23_G24":
        status="HOLD_INDEPENDENT_GATES_REQUIRED"
        blockers.append("Fresh scope-bound G23/G24 and owner authorization are absent.")
        routes=["PRESERVE_CHECKPOINT","PREPARE_EXTERNAL_GATE_REQUEST","ACTUAL_INDEPENDENT_REVIEW"]
    elif row["status"]=="COMPLETE_READONLY_UNCERTIFIED":
        status="READONLY_WORK_COMPLETE_UNCERTIFIED"
        routes=["GENERATE_EVIDENCE_REPORT","REQUEST_EXTERNAL_VALIDATION_WHEN_APPLICABLE"]
    elif now >= elastic.deadline(mission["deadline_utc"]):
        status="HOLD_EXPIRED_OWNER_REVISION_REQUIRED"
        blockers.append("Signed new owner deadline/mission revision required; no implicit extension.")
        routes=["PRESERVE_CHECKPOINT","REQUEST_SIGNED_TIME_CONTRACT"]
    elif idx >= mission["max_auto_steps"]:
        status="HOLD_AUTOMATION_STEP_BUDGET"
        blockers.append("The original owner-specified autonomous-step budget was exhausted.")
        routes=["PRESERVE_CHECKPOINT","REQUEST_NEW_SIGNED_MISSION_REVISION"]
    elif resource:
        status=resource
        blockers.append("Current host resource measurements prevent a new step.")
        routes=["REDUCE_NONCRITICAL_LOAD_IF_PREAUTHORIZED","DEFER_NEXT_READONLY_TICK","REOBSERVE_AFTER_BACKOFF"]
    elif idx >= len(steps):
        status="HOLD_STATE_INCONSISTENCY"
        blockers.append("Step index exceeds admitted plan without terminal state.")
        routes=["STOP_AND_FORENSIC_RECONCILIATION"]
    elif steps[idx]["kind"]=="GATED_OPERATION":
        status="HOLD_INDEPENDENT_GATES_REQUIRED"
        blockers.append("A requested privileged operation requires new G23/G24; no inherited certification.")
        routes=["PRESERVE_CHECKPOINT","PREPARE_EXTERNAL_GATE_REQUEST","ACTUAL_INDEPENDENT_REVIEW"]
    elif not same_uid_socket_verified and not github_runner_live_verified:
        status="HOLD_NO_LIVE_EXECUTION_CHANNEL"
        blockers.append("No authenticated live local or currently evidenced GitHub execution channel.")
        routes=["CHECK_EXISTING_OWNER_RUNNER","CHECK_LOCAL_SOCKET","REQUEST_EXACT_OWNER_CHANNEL_ACTION"]
    elif steps[idx]["kind"] in ("OBSERVE_LOCAL","INDEX_PRIORITY"):
        status="READY_REGISTERED_READONLY_STEP"
        routes=["SCHEDULER_TICK_READONLY","RECORD_RECEIPT","RECHECK_RESOURCE_AND_DEADLINE"]
    else:
        status="HOLD_UNREGISTERED_STEP"
        blockers.append("Proposed capability not present in the reviewed registry.")
        routes=["CREATE_CAPABILITY_PROPOSAL_FOR_CUSTOSZ_V7"]
    return {
        "schema":SCHEMA,"status":status,"mission_id":mission_id,
        "next_step":idx,"steps_remaining":max(0,len(steps)-idx),
        "review_passes":[
            "GOAL_OWNER_VS_MODEL_CONTRAST",
            "PROVENANCE_AND_CLAIM_VALIDITY_CHECK",
            "CAPABILITY_RESOURCE_CHANNEL_AND_GATE_CHECK"
        ],
        "channel_status":channel,"blockers":blockers,"next_route":routes,
        "retry_policy":"ONE_READONLY_TICK_PER_INVOCATION_NO_RETRY_STORM",
        "next_action_executed":False,**audit
    }


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--state-dir",required=True)
    parser.add_argument("--contract",default=str(Path(__file__).with_name("CONTRACT.v0.json")))
    parser.add_argument("--mission-id",required=True)
    args=parser.parse_args(argv)
    try:
        contract=json.loads(Path(args.contract).read_text(encoding="utf-8"))
        engine=elastic.Automation(args.state_dir,contract)
        result=diagnose(engine,args.mission_id)
        engine.ledger.append("METACOGNITIVE_DIAGNOSIS",{
            "mission_id":args.mission_id,"state":result["status"],
            "diagnosis_sha256":base.digest(result),
            "next_action_executed":False
        })
        print(json.dumps(result,indent=2,sort_keys=True))
        return 0 if not result["status"].startswith("HOLD") else 3
    except Exception as exc:
        print(json.dumps({"status":"HOLD","reason":str(exc)[:200],
                          "next_action_executed":False}),file=sys.stderr)
        return 3


if __name__=="__main__":
    sys.exit(main())
