#!/usr/bin/env python3
"""Fail-closed static validator for the Lunita v1.8 Kestra evidence gate."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
COMPOSE = (ROOT / "compose.yml").read_text(encoding="utf-8")
FLOW_PATH = ROOT / "flows" / "30-lunita-v1-8-certification-gate.yml"
FLOW = FLOW_PATH.read_text(encoding="utf-8")
GOVERNANCE = json.loads((ROOT / "GOVERNANCE.json").read_text(encoding="utf-8"))
ERRORS: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        ERRORS.append(message)


require("image: kestra/kestra:v2.0.3" in COMPOSE,
        "Kestra must use the reviewed non-floating v2.0.3 image.")
require("image: postgres:18.6-alpine" in COMPOSE,
        "PostgreSQL must use the reviewed 18.6-alpine image.")
require(":latest" not in COMPOSE,
        "Floating image tags are prohibited.")
require("/var/run/docker.sock" not in COMPOSE,
        "The host Docker socket must never be mounted.")
require('"127.0.0.1:8080:8080"' in COMPOSE
        and '"127.0.0.1:18081:8081"' in COMPOSE,
        "Kestra UI and management ports must remain loopback-only.")
require("network_mode: none" in COMPOSE and "cap_add:" in COMPOSE
        and "      - CHOWN" in COMPOSE,
        "The one-shot storage bootstrap must remain network-isolated and CHOWN-scoped.")
kestra_start = COMPOSE.find("  kestra:")
kestra_service = COMPOSE[kestra_start:] if kestra_start >= 0 else ""
require('user: "0:0"' not in kestra_service,
        "The persistent Kestra service must not run as root.")
require("env_file:" not in kestra_service,
        "The read-only public GitHub integration must not need an encoded credential file.")
require("allowed-list:" in kestra_service and "https://api.github.com" in kestra_service,
        "Kestra HTTP tasks must be restricted to the GitHub API host.")
require("KESTRA_DB_PASSWORD" in COMPOSE and "KESTRA_ADMIN_PASSWORD" in COMPOSE,
        "Local database and UI credentials must remain externally supplied.")

lower = FLOW.lower()
require("id: lunita_v1_8_certification_gate" in FLOW
        and "namespace: louksna.lunita" in FLOW,
        "The v1.8 gate must be registered under the Lunita namespace.")
require(lower.count("type: io.kestra.plugin.core.http.request") >= 4,
        "The flow must retrieve branch, CI, artifact and target evidence.")
require("method: get" in lower,
        "The evidence coordinator must use read-only GET requests.")
require("io.kestra.plugin.core.runner.process" not in lower
        and "io.kestra.plugin.scripts." not in lower,
        "Process and script tasks are prohibited before an isolated runner is approved.")
require("docker.sock" not in lower,
        "The flow must not reference the host Docker socket.")
require("schedule:" not in lower and "triggers:" not in lower,
        "The gate remains manually or CI invoked; no unverified persistent schedule.")
require("lunita-engine-overlay-v1-py312" in FLOW,
        "The gate must require the expected v1.8 overlay artifact.")
require("PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED" in FLOW,
        "The gate must require the exact non-certifying target pass status.")
require("worker_version == 'CUSTOSZ_V7'" in FLOW
        and "engine_ids_covered[13] == 'E15'" in FLOW,
        "The target receipt must bind to CUSTOSZ_V7 and cover consensus E15.")
require("G23=NOT_PERFORMED" in FLOW and "G24=NOT_GRANTED" in FLOW
        and "certification=NOT_GRANTED" in FLOW,
        "Kestra must never infer independent validation or grant certification.")

require(GOVERNANCE.get("overall_status") == "CANDIDATE_NOT_CERTIFIED",
        "The candidate must remain explicitly not certified.")
require(GOVERNANCE.get("activation") == "READ_ONLY_EVIDENCE_ORCHESTRATION_ONLY",
        "Only read-only evidence orchestration is authorized.")
gates = GOVERNANCE.get("gates", {})
require(gates.get("G23") == "NOT_PERFORMED"
        and gates.get("G24") == "NOT_GRANTED",
        "G23 and G24 must remain separate and ungranted.")
require(GOVERNANCE.get("fail_closed") is True
        and GOVERNANCE.get("certification") == "NOT_GRANTED",
        "Governance must remain fail-closed and uncertified.")

if ERRORS:
    print("FAIL_CLOSED")
    for error in ERRORS:
        print(f"- {error}")
    sys.exit(1)

print("PASS: Lunita Kestra governance and flow contract")
print("LIMIT: static validation does not execute target engines or grant G23/G24")
