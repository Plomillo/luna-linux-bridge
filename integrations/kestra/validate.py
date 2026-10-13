#!/usr/bin/env python3
"""Fail-closed static guard for the staged Kestra Open Source integration."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPOSE = (ROOT / "compose.yml").read_text(encoding="utf-8")
ENV_EXAMPLE = (ROOT / ".env.example").read_text(encoding="utf-8")
GOVERNANCE = json.loads((ROOT / "GOVERNANCE.json").read_text(encoding="utf-8"))
errors: list[str] = []

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

require("image: kestra/kestra:v2.0.3" in COMPOSE,
        "Kestra must stay on the reviewed full-image patch tag v2.0.3.")
require("image: postgres:18.6-alpine" in COMPOSE,
        "PostgreSQL must stay on the reviewed patch tag 18.6-alpine.")
require(":latest" not in COMPOSE,
        "Floating :latest image tags are prohibited.")
require("/var/run/docker.sock" not in COMPOSE,
        "Mounting the host Docker socket is prohibited.")
require('"127.0.0.1:8080:8080"' in COMPOSE,
        "UI must remain bound to loopback.")
require('"127.0.0.1:18081:8081"' in COMPOSE,
        "Unauthenticated management endpoint must remain loopback-only.")
require("basic-auth:" in COMPOSE and "enabled: true" in COMPOSE,
        "Basic authentication must remain enabled.")
require("endpoints:\\n          all:\\n            basic-auth:" in COMPOSE,
        "Management endpoint details must require authentication.")
require("REPLACE_WITH_" in ENV_EXAMPLE,
        ".env.example must contain placeholders, not deployable credentials.")
require(GOVERNANCE.get("overall_status") == "CANDIDATE_NOT_CERTIFIED",
        "The integration must not self-promote to certified.")
require(GOVERNANCE.get("gates", {}).get("G23") == "NOT_PERFORMED",
        "G23 must remain unperformed until independent validation.")
require(GOVERNANCE.get("gates", {}).get("G24") == "NOT_GRANTED",
        "G24 must remain not granted.")
require(GOVERNANCE.get("activation") == "NOT_AUTHORIZED",
        "Activation/promotion must remain unauthorized.")

flows = ROOT / "flows"
for flow_path in sorted(flows.rglob("*.yml")) + sorted(flows.rglob("*.yaml")):
    body = flow_path.read_text(encoding="utf-8")
    lower = body.lower()
    require("io.kestra.plugin.core.runner.process" not in lower,
            f"{flow_path.relative_to(ROOT)} uses the non-isolated Process runner.")
    require("io.kestra.plugin.scripts." not in lower,
            f"{flow_path.relative_to(ROOT)} declares script execution before runner isolation is approved.")
    require("docker.sock" not in lower,
            f"{flow_path.relative_to(ROOT)} references a Docker socket.")
    require("schedule:" not in lower and "triggers:" not in lower,
            f"{flow_path.relative_to(ROOT)} must not schedule or trigger itself during the staged phase.")

if errors:
    print("FAIL_CLOSED")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("PASS: staged Kestra governance invariants")
print("LIMIT: static checks do not certify runtime behavior, task execution, G23, or G24")
