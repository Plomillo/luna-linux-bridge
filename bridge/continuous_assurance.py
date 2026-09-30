#!/usr/bin/env python3
"""PUAC2-aligned continuous G23/G24 readiness checks for LOUKSNA Remote Bridge.

Checks evidence presence and source identity throughout the lifecycle, not just
at release. This program DOES NOT act as G23, G24, independent identity attestor,
signing authority or material executor. The existing external_gates verifier is
the ONLY cryptographic preflight interface for production requests.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import lrb_core as base

SCHEMA = "LRB_CONTINUOUS_ASSURANCE/0.1"
PHASES = ("INTAKE", "DEVELOPMENT", "INTEGRATION", "PRE_RELEASE", "POSTBOOT")
STREAMS = ("TRUST_AND_CERTIFICATION", "GOVERNANCE", "EXECUTION_AND_OBSERVABILITY",
           "CONTINUITY_AND_GUARANTEES")
ROLES = ("G23", "G24")
HEX40 = re.compile(r"^[a-f0-9]{40}$")
HEX64 = re.compile(r"^[a-f0-9]{64}$")
MAX_BYTES = 65536


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 1024


def _unique_strings(values):
    return isinstance(values, list) and 1 <= len(values) <= 16 and all(
        _nonempty(value) for value in values) and len(set(values)) == len(values)


def validate_plan(plan):
    if not isinstance(plan, dict) or set(plan) != {
        "schema", "authority", "supporting_protocol", "status", "doctrine",
        "workstreams", "lifecycle", "activation_contract"}:
        raise RuntimeError("ASSURANCE_PLAN_SCHEMA_OR_FIELDS_INVALID")
    if (plan["schema"] != SCHEMA or plan["authority"] != "Louksna.md"
            or plan["supporting_protocol"] != "PUAC2.md"
            or plan["status"] != "DESIGN_ONLY_UNCERTIFIED"
            or plan["doctrine"] != "EXTEND_DO_NOT_REPLACE"):
        raise RuntimeError("CANONICAL_ASSURANCE_AUTHORITY_DRIFT")
    if plan["lifecycle"] != list(PHASES):
        raise RuntimeError("LIFECYCLE_PHASES_INCOMPLETE_OR_REORDERED")
    contract = plan["activation_contract"]
    if not isinstance(contract, dict) or contract != {
        "g23": "INDEPENDENT_VALIDATION",
        "g24": "CERTIFICATION_AFTER_FAVORABLE_G23",
        "second_order": ["G23_2", "G24_2"],
        "all_phases_have_g23_g24_prechecks": True,
        "new_scope_requires_fresh_decisions": True,
        "historic_certification_is_not_current_authorization": True,
        "independent_signer_custody_must_be_externally_attested": True,
        "release_requires_verified_production_signatures": True,
        "postboot_requires_new_boot_scoped_review_if_changed": True
    }:
        raise RuntimeError("ASSURANCE_ACTIVATION_CONTRACT_DRIFT")
    streams = plan["workstreams"]
    if (not isinstance(streams, list) or len(streams) != len(STREAMS)
            or [s.get("id") if isinstance(s,dict) else None for s in streams] != list(STREAMS)):
        raise RuntimeError("REQUIRED_WORKSTREAM_MISSING_OR_REORDERED")
    for stream in streams:
        if set(stream) != {"id", "owner_requirement", "claim", "acceptance", "verification",
                           "validation", "risks", "dependencies", "execution_responsible",
                           "phases"}:
            raise RuntimeError("WORKSTREAM_EVIDENCE_CONTRACT_INCOMPLETE")
        if not all(_nonempty(stream[key]) for key in
                   ("owner_requirement", "claim", "acceptance", "verification",
                    "validation", "execution_responsible")):
            raise RuntimeError("CRITICAL_REQUIREMENT_WITHOUT_VERIFIABLE_CRITERION")
        if not _unique_strings(stream["risks"]) or not _unique_strings(stream["dependencies"]):
            raise RuntimeError("RISK_OR_DEPENDENCY_UNACCOUNTED")
        phase_map = stream["phases"]
        if not isinstance(phase_map, dict) or list(phase_map) != list(PHASES):
            raise RuntimeError("PHASE_GATE_GAP_OR_ORDER_DRIFT")
        for phase in PHASES:
            row = phase_map[phase]
            if not isinstance(row, dict) or set(row) != {
                "object_and_version", "expected_evidence", "impact_review",
                "rollback_condition", "G23", "G24"}:
                raise RuntimeError("PHASE_ASSURANCE_FIELD_MISSING")
            if not all(_nonempty(row[key]) for key in
                       ("object_and_version", "impact_review", "rollback_condition")):
                raise RuntimeError("PHASE_CONTROL_UNSPECIFIED")
            if not _unique_strings(row["expected_evidence"]):
                raise RuntimeError("PHASE_WITHOUT_EVIDENCE_TARGETS")
            for role in ROLES:
                gate = row[role]
                if not isinstance(gate, dict) or set(gate) != {
                    "role", "expected_evidence", "decision_authority",
                    "status"}:
                    raise RuntimeError("G23_G24_PHASE_PRESENCE_REQUIRED")
                if (gate["role"] != role or gate["status"] != "PENDING_INDEPENDENT_DECISION"
                        or gate["decision_authority"] != (
                            "INDEPENDENT_VALIDATOR" if role == "G23"
                            else "SEPARATE_CERTIFICATION_AUTHORITY")
                        or not _unique_strings(gate["expected_evidence"])):
                    raise RuntimeError("G23_G24_CANNOT_BE_SUBSTITUTED_OR_SELF_APPROVED")
    return base.digest(plan)


def evaluate(plan, source_commit, evidence=None):
    plan_sha = validate_plan(plan)
    if not isinstance(source_commit, str) or not HEX40.fullmatch(source_commit):
        raise RuntimeError("EXACT_COMMIT_SHA_REQUIRED")
    # Externally supplied evidence references are inventory only. A hash or a
    # GitHub run ID never authenticates an independent human decision.
    if evidence is None:
        evidence = []
    if not isinstance(evidence, list) or len(evidence) > 200:
        raise RuntimeError("BOUNDED_EVIDENCE_REGISTRY_REQUIRED")
    seen=set()
    for row in evidence:
        if (not isinstance(row, dict) or set(row) != {
            "evidence_id", "workstream", "phase", "role", "source_commit",
            "sha256", "source", "claim", "status"}
                or not _nonempty(row["evidence_id"])
                or row["evidence_id"] in seen or row["workstream"] not in STREAMS
                or row["phase"] not in PHASES or row["role"] not in ROLES
                or row["source_commit"] != source_commit
                or not isinstance(row["sha256"], str) or not HEX64.fullmatch(row["sha256"])
                or not _nonempty(row["source"]) or not _nonempty(row["claim"])
                or row["status"] != "REFERENCED_UNAUTHENTICATED"):
            raise RuntimeError("UNTRUSTED_OR_CROSS_COMMIT_EVIDENCE_DENIED")
        seen.add(row["evidence_id"])
    index={(row["workstream"], row["phase"], row["role"]): [] for row in evidence}
    for row in evidence:
        index[(row["workstream"], row["phase"], row["role"])].append(row["evidence_id"])
    lifecycle=[]
    missing=0
    for phase in PHASES:
        workstreams=[]
        for s in plan["workstreams"]:
            role_evidence={k:index.get((s["id"],phase,k),[]) for k in ROLES}
            missing += sum(1 for values in role_evidence.values() if not values)
            workstreams.append({
                "id":s["id"],
                "g23":{"plan":"DEFINED_AT_DESIGN","evidence_refs":role_evidence["G23"],
                       "decision":"NOT_ISSUED_OR_NOT_INDEPENDENTLY_VERIFIED"},
                "g24":{"plan":"DEFINED_AT_DESIGN","evidence_refs":role_evidence["G24"],
                       "decision":"BLOCKED_UNTIL_FAVORABLE_INDEPENDENT_G23"},
                "work_product":"REFERENCE_ONLY_NOT_ATTESTED",
                "can_operationally_activate":False})
        lifecycle.append({"phase":phase,"workstreams":workstreams,
            "g23_and_g24_included_in_every_workstream":True,
            "gates_certified":False})
    return {"schema":SCHEMA, "subject_commit":source_commit,
            "plan_sha256":plan_sha,
            "phase_order":list(PHASES), "workstream_count":len(STREAMS),
            "gate_slots":len(PHASES)*len(STREAMS)*len(ROLES),
            "gate_slots_without_evidence_ref":missing,
            "parallel_prechecks":["G23_EVIDENCE_AND_INDEPENDENCE_REVIEW",
                                  "G24_CRITERIA_AND_SCOPE_READINESS"],
            "serial_decision_dependency":"FAVORABLE_G23_BEFORE_G24",
            "life_cycle":lifecycle,
            "actual_independent_signatures_verified":False,
            "actual_signer_custody_attested":False,
            "historic_certification_reused":False,
            "root_or_disk_mutation_authorized":False,
            "release_status":"HOLD_EXTERNAL_G23_G24_AND_SECOND_ORDER",
            "certified":False}


def _read(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size > MAX_BYTES:
        raise RuntimeError("LIFECYCLE_INPUT_UNSAFE")
    return json.loads(p.read_text(encoding="utf-8"))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan",default=str(Path(__file__).with_name("ASSURANCE_MATRIX.json")))
    parser.add_argument("--commit",required=True)
    parser.add_argument("--evidence")
    parser.add_argument("--out",required=True)
    args=parser.parse_args(argv)
    try:
        plan=_read(args.plan)
        evidence=_read(args.evidence) if args.evidence else []
        result=evaluate(plan,args.commit,evidence)
        out=Path(args.out)
        if out.is_symlink() or not out.parent.is_dir() or out.exists():
            raise RuntimeError("OUTPUT_NOT_FRESH_OR_PARENT_INVALID")
        fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:
            data=json.dumps(result,sort_keys=True,indent=2).encode()+b"\n"
            with os.fdopen(fd,"wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            try:out.unlink()
            except OSError:pass
            raise
        print(json.dumps({"status":"DESIGN_AND_GATE_COVERAGE_CHECKED_UNCERTIFIED",
                          "plan_sha256":result["plan_sha256"],
                          "gate_slots":result["gate_slots"],
                          "missing_evidence_refs":result["gate_slots_without_evidence_ref"],
                          "release_status":result["release_status"]},sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status":"HOLD","reason":str(exc)[:150],"certified":False}),file=sys.stderr)
        return 3


if __name__=="__main__":
    raise SystemExit(main())
