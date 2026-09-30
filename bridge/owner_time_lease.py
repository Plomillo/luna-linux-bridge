#!/usr/bin/env python3
"""Hot-extend ONLY the nonprivileged observer's budget with real owner signature.

Does not extend mission deadlines, existing G23/G24 scope, sudo, privileged
leases, source code authority or the immutable contract's hard maximum.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone, timedelta
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import lrb_core as base
from external_gates import ExternalGateVerifier, read_regular, parse_utc

SCHEMA="LRB_SIGNED_OWNER_READONLY_TIME_LEASE/0.4"
SAFE_ID=re.compile(r"^[A-Za-z0-9_-]{16,80}$")
MAX_AGE=timedelta(minutes=15)


def apply_lease(state, contract, contract_path, lease_path, signature_path,
                verifier=None, clock=None):
    state=base.secure_state(state)
    clock=clock or (lambda:datetime.now(timezone.utc))
    # Ownership validation and pinned key selection occur in verifier init.
    if verifier is None:
        verifier=ExternalGateVerifier("/etc/louksna/remote-bridge",
                                      enforce_root_owned=True)
    verifier.sig("OWNER",lease_path,signature_path)
    raw=read_regular(lease_path)
    lease=json.loads(raw)
    required={"schema","lease_id","owner_intent","host","boot_id",
              "contract_sha256","controller_sha256","expected_revision",
              "heartbeat_sec","max_work_seconds","issued_utc","expires_utc"}
    if set(lease)!=required or lease.get("schema")!=SCHEMA:
        raise RuntimeError("OWNER_TIME_LEASE_FIELDS_UNREVIEWED")
    if not isinstance(lease.get("lease_id"),str) or not SAFE_ID.fullmatch(lease["lease_id"]):
        raise RuntimeError("OWNER_TIME_LEASE_ID_INVALID")
    if lease["owner_intent"]!="EXPLICIT_NONPRIVILEGED_BUDGET_CHANGE":
        raise RuntimeError("TIME_LEASE_MAY_NOT_AUTHORIZE_ROOT")
    if lease["host"]!=os.uname().nodename or lease["boot_id"]!=base.boot_id():
        raise RuntimeError("OWNER_TIME_LEASE_HOST_OR_BOOT_DRIFT")
    contract_raw=read_regular(contract_path)
    if (hashlib.sha256(contract_raw).hexdigest()!=lease["contract_sha256"]
            or hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=lease["controller_sha256"]):
        raise RuntimeError("OWNER_TIME_LEASE_SOURCE_OR_CONTRACT_DRIFT")
    limits=contract.get("resource_defaults",{})
    if (contract.get("schema")!="LOUKSNA_REMOTE_BRIDGE_CONTRACT/0.1"
            or contract.get("release",{}).get("certified") is not False):
        raise RuntimeError("OWNER_TIME_LEASE_CONTRACT_UNTRUSTED")
    new_work=lease["max_work_seconds"]
    heartbeat=lease["heartbeat_sec"]
    revision=lease["expected_revision"]
    if (type(new_work) is not int or not 1<=new_work<=limits["hard_deadline_sec"]
            or type(heartbeat) is not int or
            not limits["min_heartbeat_sec"]<=heartbeat<=limits["max_heartbeat_sec"]
            or type(revision) is not int or revision<0):
        raise RuntimeError("OWNER_TIME_LEASE_HARD_LIMIT_OR_TYPE")
    now=clock()
    issued=parse_utc(lease["issued_utc"])
    expires=parse_utc(lease["expires_utc"])
    if (now.tzinfo is None or now.utcoffset()!=timedelta(0)
            or issued>now+timedelta(seconds=30) or now>=expires
            or expires<=issued or expires-issued>MAX_AGE):
        raise RuntimeError("OWNER_TIME_LEASE_STALE")
    lock=state/"TIME_POLICY.lock"
    with lock.open("a+b") as mutex:
        fcntl.flock(mutex,fcntl.LOCK_EX)
        ledger=base.EvidenceLedger(state)
        ledger.verify()
        previous=base.load_time_policy(state,contract)
        if previous["revision"]!=revision:
            raise RuntimeError("OWNER_TIME_LEASE_REVISION_COLLISION")
        if new_work<=previous["max_work_seconds"]:
            raise RuntimeError("ONLY_REAL_EXTENSION_REQUIRES_SIGNED_LEASE")
        if new_work>previous["hard_deadline_sec"]:
            raise RuntimeError("OWNER_TIME_LEASE_EXCEEDS_IMMUTABLE_CEILING")
        for item in ledger._records():
            if item["kind"]=="OWNER_LEASE_COMMIT" and item["payload"]["lease_id"]==lease["lease_id"]:
                raise RuntimeError("OWNER_TIME_LEASE_REPLAY")
        new={**previous,"revision":revision+1,"heartbeat_sec":heartbeat,
             "max_work_seconds":new_work}
        payload={"lease_id":lease["lease_id"],
                 "signed_lease_sha256":hashlib.sha256(raw).hexdigest(),
                 "signature_sha256":hashlib.sha256(read_regular(signature_path,8192)).hexdigest(),
                 "previous_revision":revision,
                 "new_revision":revision+1,
                 "old_max_work_seconds":previous["max_work_seconds"],
                 "new_max_work_seconds":new_work,
                 "root_privilege_extended":False}
        ledger.append("OWNER_LEASE_INTENT",payload)
        base.atomic_json(state/"TIME_POLICY.json",new)
        ledger.append("OWNER_LEASE_COMMIT",payload)
    return {"schema":SCHEMA,"status":"SIGNED_NONPRIVILEGED_TIME_POLICY_UPDATED",
            "lease_id":lease["lease_id"],"old_seconds":previous["max_work_seconds"],
            "new_seconds":new_work,"revision":new["revision"],
            "existing_mission_deadlines_extended":False,
            "existing_g23_g24_extended":False,
            "root_privilege_extended":False,"certified":False}


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--state-dir",required=True)
    p.add_argument("--contract",default=str(Path(__file__).with_name("CONTRACT.v0.json")))
    p.add_argument("--lease",required=True)
    p.add_argument("--signature",required=True)
    args=p.parse_args(argv)
    try:
        contract=json.loads(read_regular(args.contract))
        result=apply_lease(args.state_dir,contract,args.contract,args.lease,args.signature)
        print(json.dumps(result,indent=2,sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status":"HOLD","reason":str(exc)[:160],
                          "privileged":False,"certified":False}),file=sys.stderr)
        return 3


if __name__=="__main__":
    sys.exit(main())
