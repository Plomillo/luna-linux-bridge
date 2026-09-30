#!/usr/bin/env python3
"""Deterministic LLM accountability gate; never a model, independent G23 or G24.

Produces actionable corrections without silently rewriting the owner's goal.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

import lrb_core as base

SCHEMA = "LRB_MODEL_HANDRAIL/0.1"
CLAIMS = {"OBSERVED", "INFERRED", "PREPARED", "EXECUTED", "VERIFIED",
          "VALIDATED", "CERTIFIED", "PROPOSED"}
KNOWN_CHANNEL = "GITHUB_RUNNER_READONLY"


def review(envelope, evidence):
    if not isinstance(envelope, dict) or not isinstance(evidence, dict):
        raise RuntimeError("STRUCTURED_REVIEW_INPUT_REQUIRED")
    if envelope.get("schema") != SCHEMA:
        raise RuntimeError("HANDRAIL_SCHEMA_MISMATCH")
    corrections = []
    def require(condition, code, instruction):
        if not condition:
            corrections.append({"code": code, "required_correction": instruction})

    goal = envelope.get("user_objective")
    proposal = envelope.get("model_expectation")
    require(isinstance(goal, str) and bool(goal.strip()), "OWNER_GOAL_MISSING",
            "Restate the owner's exact objective without rewriting it.")
    require(isinstance(proposal, str), "MODEL_EXPECTATION_NOT_SEPARATE",
            "State the model's proposed approach in a separate field.")
    declared = envelope.get("model", {})
    require(isinstance(declared, dict) and
            all(isinstance(declared.get(k), str) and declared[k].strip()
                for k in ("name", "version")), "MODEL_VERSION_MISSING",
            "Declare the model name and version; label identity as self-reported.")
    if isinstance(declared, dict):
        require(declared.get("provider_verified") is False,
                "MODEL_IDENTITY_OVERCLAIM",
                "Use provider_verified=false without a separate authenticated identity proof.")
    inv = envelope.get("tool_inventory")
    require(isinstance(inv, list) and len(inv) <= 64 and
            all(isinstance(x, dict) and isinstance(x.get("name"), str) and
                x.get("state") in ("AVAILABLE", "UNAVAILABLE", "UNKNOWN") for x in inv),
            "TOOL_INVENTORY_REQUIRED",
            "Report available, unavailable and unknown tools distinctly.")
    observations = evidence.get("observations", {})
    require(isinstance(observations, dict), "EVIDENCE_REGISTRY_REQUIRED",
            "Provide a registry of immutable evidence references and their hashes.")
    if not isinstance(observations, dict):
        observations = {}
    claims = envelope.get("claims")
    require(isinstance(claims, list) and 0 < len(claims) <= 40,
            "BOUNDED_CLAIM_LEDGER_REQUIRED", "List each material claim with its epistemic state.")
    if not isinstance(claims, list):
        claims = []
    for number, item in enumerate(claims[:40]):
        if not isinstance(item, dict) or item.get("state") not in CLAIMS or (
            not isinstance(item.get("statement"), str) or not item["statement"].strip()):
            require(False, "CLAIM_INVALID_" + str(number),
                    "Supply a bounded claim with an explicit state and nonempty statement.")
            continue
        state = item["state"]
        refs = item.get("evidence_refs", [])
        if state in ("OBSERVED", "EXECUTED", "VERIFIED", "VALIDATED", "CERTIFIED"):
            valid_refs = isinstance(refs, list) and bool(refs) and all(
                isinstance(ref, str) and ref in observations and
                isinstance(observations[ref], dict) and
                isinstance(observations[ref].get("sha256"), str) and
                len(observations[ref]["sha256"]) == 64 and
                all(c in "0123456789abcdef" for c in observations[ref]["sha256"])
                for ref in refs)
            require(valid_refs, "UNBOUND_EVIDENCE_" + str(number),
                    "Cite actual immutable evidence references; unverified references do not establish truth.")
        if state in ("VERIFIED", "VALIDATED", "CERTIFIED"):
            require(False, "INDEPENDENT_VERIFICATION_NOT_PERFORMED_" + str(number),
                    "Downgrade to an evidential description pending independent verified provenance and external gates.")
        if state == "EXECUTED":
            require(item.get("tool_receipt_id") in observations,
                    "MISSING_EXECUTION_RECEIPT_" + str(number),
                    "Bind the claim to the actual tool run's receipt, not the script text.")
    route = envelope.get("next_action")
    require(isinstance(route, dict) and bool(route.get("action")) and
            route.get("kind") in ("READONLY_REGISTERED", "PROPOSE_GATED", "HUMAN_ACTION"),
            "ACTIONABLE_ROUTE_MISSING",
            "Provide one named registered read-only action, a gated proposal, or one exact human dependency.")
    if isinstance(route, dict) and route.get("kind") == "PROPOSE_GATED":
        require(route.get("fresh_g23") is False and route.get("fresh_g24") is False and
                route.get("execution_authorized") is False,
                "GATED_AUTHORITY_OVERCLAIM",
                "State that fresh independent G23/G24 are NOT executed and execution is NOT authorized.")
    if isinstance(route, dict) and route.get("kind") == "READONLY_REGISTERED":
        require(route.get("action") in ("OBSERVE_LOCAL", "INDEX_PRIORITY"),
                "READONLY_CAPABILITY_UNKNOWN",
                "Use a registered read-only function; propose a new capability rather than guess.")
    if isinstance(inv, list):
        available = {t.get("name") for t in inv if isinstance(t, dict) and t.get("state") == "AVAILABLE"}
        if KNOWN_CHANNEL in available:
            require(envelope.get("github_runner_considered") is True,
                    "AVAILABLE_CHANNEL_IGNORED",
                    "Evaluate existing GitHub-to-host runner evidence before claiming no remote access.")
    review_budget = envelope.get("pro_operational_review", {})
    require(isinstance(review_budget, dict) and type(review_budget.get("rounds_completed")) is int
            and 0 <= review_budget.get("rounds_completed", -1) <= 8
            and type(review_budget.get("negative_tests_checked")) is int
            and 0 <= review_budget.get("negative_tests_checked", -1) <= 100,
            "PRO_EFFORT_ACCOUNTABILITY",
            "Report bounded completed review passes and negative checks, not ChatGPT Pro entitlement.")
    if isinstance(review_budget, dict):
        require(review_budget.get("claim_of_chatgpt_pro_control") is False,
                "PRO_PRODUCT_MODE_OVERCLAIM",
                "State that the Bridge does not control ChatGPT subscription or hidden reasoning effort.")
    require(envelope.get("claimed_certified") is False,
            "CERTIFICATION_SELF_ASSERTION",
            "Certification requires independent G23/G24 and separate second-order signers.")
    return {"schema": SCHEMA, "status": "CORRECTION_REQUIRED" if corrections else
            "STRUCTURAL_REVIEW_PASS_UNCERTIFIED",
            "corrections": corrections, "input_sha256": base.digest(envelope),
            "evidence_index_sha256": base.digest(evidence), "certified": False,
            "independent_evidence_verified": False,
            "next_allowed_phase": "MODEL_REVISION" if corrections else "EXTERNAL_REVIEW_REQUIRED"}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--envelope", required=True)
    parser.add_argument("--evidence-index", required=True)
    parser.add_argument("--state-dir", required=True)
    args = parser.parse_args(argv)
    try:
        p, q = Path(args.envelope), Path(args.evidence_index)
        for file in (p, q):
            if file.is_symlink() or file.stat().st_size > 64 * 1024:
                raise RuntimeError("REVIEW_INPUT_UNSAFE_OR_UNBOUNDED")
        envelope = json.loads(p.read_text())
        evidence = json.loads(q.read_text())
        report = review(envelope, evidence)
        ledger = base.EvidenceLedger(base.secure_state(args.state_dir))
        ledger.append("LLM_ACCOUNTABILITY_REVIEW", {
            "envelope_sha256": report["input_sha256"],
            "index_sha256": report["evidence_index_sha256"],
            "codes": [item["code"] for item in report["corrections"]],
            "status": report["status"], "certified": False
        })
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if not report["corrections"] else 3
    except Exception as exc:
        print(json.dumps({"status": "HOLD", "reason": str(exc)[:200]}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
