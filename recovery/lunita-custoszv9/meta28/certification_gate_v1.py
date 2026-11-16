"""META-28 certification gate.

Writes the required report set from observed facts. It cannot grant
certification: the size lower bound exceeds 515000000 and no SquashFS
image was produced. v1.8 axioms are not amended.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from consensus_v1 import evaluate as evaluate_consensus
from documents_v1 import FORMATS, compatibility
from epistemic_v1 import EpistemicError, promote
from size_budget_v1 import HARD_MAX_BYTES, evaluate, meta28_default_payloads

OBSERVED_AT = "2026-11-16T20:13:00Z"
CANDIDATE_ID = "LUNITA_META_28"
BASE_COMMIT = "9d4b53fc81728baa9bf35a96e776af9744776563"
BASE_BRANCH = "fix/lunita-v18-rootfs-bound-checkpoint-20261109"
V18_CANDIDATE = "G06_REBUILD_CANDIDATE_R1"
SPEC_VERSION = "LUNITA-META-28"

TESTS = [f"T{index:02d}" for index in range(1, 81)]

REPORTS = (
    "LUNITA_BUILD_MANIFEST.json",
    "LUNITA_COMPONENT_INVENTORY.json",
    "LUNITA_DEPENDENCY_MANIFEST.json",
    "LUNITA_CONTRACT_REGISTRY.json",
    "LUNITA_TEST_RESULTS.json",
    "LUNITA_EVIDENCE_INDEX.json",
    "LUNITA_SECURITY_AUDIT.json",
    "LUNITA_ZERO_TRUST_REPORT.json",
    "LUNITA_METACOGNITIVE_REPORT.json",
    "LUNITA_RESEARCH_VALIDATION_REPORT.json",
    "LUNITA_DOCUMENT_COMPATIBILITY_REPORT.json",
    "LUNITA_ROLLBACK_REPORT.json",
    "LUNITA_INDEPENDENT_VALIDATION_REPORT.json",
    "LUNITA_CERTIFICATION_REPORT.json",
)


def _dump(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def observe() -> dict:
    size = evaluate(meta28_default_payloads())
    try:
        promote("DECLARED", "CERTIFIED", independent_validation=False)
        jumped = True
    except EpistemicError:
        jumped = False
    consensus = evaluate_consensus(
        [
            {"vote": "ACCEPT", "evidence_digest": "abc", "decision_logic_id": "qwen3", "runtime_id": "llama.cpp"},
            {"vote": "ACCEPT", "evidence_digest": "abc", "decision_logic_id": "qwen3", "runtime_id": "llama.cpp"},
        ],
        "abc",
    )
    return {
        "size": size,
        "forbidden_jump_blocked": not jumped,
        "consensus": consensus,
        "image_present": False,
    }


def write_reports(directory: Path, observed_at: str = OBSERVED_AT) -> dict:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    observed = observe()
    size = observed["size"]
    common = {
        "schema": "LUNITA_META28_OBSERVATION/1.0",
        "candidate_id": CANDIDATE_ID,
        "spec_version": SPEC_VERSION,
        "observed_at": observed_at,
        "base_branch": BASE_BRANCH,
        "base_commit": BASE_COMMIT,
        "replaces_v18": False,
        "v18_candidate_id": V18_CANDIDATE,
        "certification": "NOT_GRANTED",
        "image": None,
    }
    build = {
        **common,
        "report": "BUILD_MANIFEST",
        "status": size["status"],
        "hard_max_bytes": HARD_MAX_BYTES,
        "final_squashfs_bytes": None,
        "final_squashfs_sha256": None,
        "accounted_required_lower_bound_bytes": size["accounted_required_lower_bound_bytes"],
        "over_by_bytes": size["over_by_bytes"],
        "payloads": size["payloads"],
        "unmeasured_required": [
            "debian-13-xfce",
            "libreoffice",
            "r",
            "rstudio",
            "jasp",
            "chromium",
            "qdrant",
        ],
        "built": False,
    }
    inventory = {
        **common,
        "report": "COMPONENT_INVENTORY",
        "status": "NOT_INSTALLED",
        "identity": "LUNITA",
        "qwen3_is_identity": False,
        "engines": [f"E{index:02d}" for index in range(1, 16)],
        "instruments": ["brujula_giroscopica", "lapiz", "sacapuntas", "lupa"],
        "mailbox_modules": ["CONSULTAS", "TRABAJOS"],
        "functional_status": "NOT_RUN_NO_IMAGE",
    }
    dependencies = {
        **common,
        "report": "DEPENDENCY_MANIFEST",
        "status": "UNRESOLVED",
        "reason": "No candidate rootfs was built for META-28.",
    }
    contracts = {
        **common,
        "report": "CONTRACT_REGISTRY",
        "contract_version": "1.0",
        "schemas": ["request.schema.json", "response.schema.json"],
        "arbitrary_eval": "FORBIDDEN",
    }
    tests = {
        **common,
        "report": "TEST_RESULTS",
        "status": "NOT_RUN",
        "results": {test_id: "NOT_RUN_NO_IMAGE" for test_id in TESTS},
        "note": "Gate unit tests are not T01-T80 and cannot satisfy them.",
    }
    security = {
        **common,
        "report": "SECURITY_AUDIT",
        "status": "NOT_EXECUTED",
        "unauthorized_access_test": "NOT_RUN",
        "tamper_test": "NOT_RUN",
        "privilege_escalation_test": "NOT_RUN",
    }
    zero_trust = {
        **common,
        "report": "ZERO_TRUST",
        "status": "POLICY_ENCODED_NOT_DEMONSTRATED",
        "deny_rule_implemented": True,
        "hostile_tests_executed_on_image": False,
    }
    metacognition = {
        **common,
        "report": "METACOGNITION",
        "status": "OBSERVED_BLOCK",
        "self_observation": "SIZE_LOWER_BOUND_EXCEEDS_HARD_MAX",
        "self_correction_executed": False,
        "raised_own_limits": False,
    }
    research = {
        **common,
        "report": "RESEARCH_VALIDATION",
        "status": "NOT_RUN",
        "quantitative": "NOT_RUN",
        "qualitative": "NOT_RUN",
        "mixed": "NOT_RUN",
        "end_to_end_mission": "NOT_RUN",
    }
    documents = {
        **common,
        "report": "DOCUMENT_COMPATIBILITY",
        "status": "NOT_COMPATIBLE",
        "formats": [compatibility(fmt, "DECLARED") for fmt in FORMATS],
    }
    rollback = {
        **common,
        "report": "ROLLBACK",
        "status": "NOT_RUN",
        "reason": "No candidate image exists to roll back.",
        "levels": ["RB01", "RB02", "RB03", "RB04", "RB05"],
    }
    independent = {
        **common,
        "report": "INDEPENDENT_VALIDATION",
        "status": "NOT_PERFORMED",
        "G23": "NOT_PERFORMED",
        "G24": "NOT_GRANTED",
    }
    contradictions = [
        {
            "id": "BASE_OS",
            "meta28": "Debian GNU/Linux 13 Trixie XFCE",
            "skeleton": "Debian GNU/Linux 13 Trixie KDE Plasma",
            "v18": "Ubuntu 24.04 rootfs candidate",
            "resolution": "UNRESOLVED_HUMAN_DECISION_REQUIRED",
        },
        {
            "id": "SIZE",
            "meta28_hard_max_bytes": HARD_MAX_BYTES,
            "required_lower_bound_bytes": size["accounted_required_lower_bound_bytes"],
            "resolution": "BUILD_BLOCKED_BY_SIZE_CONSTRAINT",
        },
        {
            "id": "IDENTITY_LINE",
            "meta28_candidate": CANDIDATE_ID,
            "preserved_candidate": V18_CANDIDATE,
            "resolution": "EXTEND_DO_NOT_REPLACE",
        },
    ]
    certification = {
        **common,
        "report": "CERTIFICATION",
        "status": "CERTIFICATION_BLOCKED",
        "predicate": "ADMIT(image) is false because image is absent and AX-M28-021 size gate failed",
        "forbidden_jump_blocked": observed["forbidden_jump_blocked"],
        "consensus_status": observed["consensus"]["status"],
        "contradictions": contradictions,
        "human_decision_required": [
            "Raise GLOBAL_LUNITA_HARD_MAX_BYTES to a measured envelope, or",
            "Amend META-28 explicitly so instruments are outside LUNITA.squashfs.",
            "Choose the binding desktop: skeleton KDE, v1.8 Ubuntu, or META-28 XFCE.",
        ],
        "silent_scope_reduction": "FORBIDDEN",
    }
    bodies = {
        "LUNITA_BUILD_MANIFEST.json": build,
        "LUNITA_COMPONENT_INVENTORY.json": inventory,
        "LUNITA_DEPENDENCY_MANIFEST.json": dependencies,
        "LUNITA_CONTRACT_REGISTRY.json": contracts,
        "LUNITA_TEST_RESULTS.json": tests,
        "LUNITA_SECURITY_AUDIT.json": security,
        "LUNITA_ZERO_TRUST_REPORT.json": zero_trust,
        "LUNITA_METACOGNITIVE_REPORT.json": metacognition,
        "LUNITA_RESEARCH_VALIDATION_REPORT.json": research,
        "LUNITA_DOCUMENT_COMPATIBILITY_REPORT.json": documents,
        "LUNITA_ROLLBACK_REPORT.json": rollback,
        "LUNITA_INDEPENDENT_VALIDATION_REPORT.json": independent,
        "LUNITA_CERTIFICATION_REPORT.json": certification,
    }
    for name, payload in bodies.items():
        _dump(directory / name, payload)
    lines = []
    index = []
    for name in REPORTS:
        if name == "LUNITA_EVIDENCE_INDEX.json":
            continue
        data = (directory / name).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        lines.append(f"{digest}  {name}")
        index.append({"name": name, "sha256": digest, "bytes": len(data)})
    (directory / "LUNITA_SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    evidence = {
        **common,
        "report": "EVIDENCE_INDEX",
        "status": "BLOCKED",
        "squashfs": "NOT_PRODUCED",
        "files": index,
        "sha256sums_sha256": hashlib.sha256((directory / "LUNITA_SHA256SUMS").read_bytes()).hexdigest(),
    }
    _dump(directory / "LUNITA_EVIDENCE_INDEX.json", evidence)
    return {
        "status": "CERTIFICATION_BLOCKED",
        "size_status": size["status"],
        "over_by_bytes": size["over_by_bytes"],
    }
