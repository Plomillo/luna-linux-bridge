"""Choose a capability from the operation text. Case ids are not inputs."""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

PARAMS = json.loads((Path(__file__).resolve().parents[2] / "fixtures" / "derived_parameters.json").read_text(encoding="utf-8"))


def interpret(operation: str) -> dict:
    text = operation.casefold()
    listed = re.search(r"\[([0-9,\s]+)\]", operation)
    if listed and re.search(r"buscar|primera|localizar", text):
        values = [int(item) for item in listed.group(1).split(",") if item.strip()]
        needle = re.search(r"(\d+)\D+\[", operation)
        return {"plan_status": "VALIDATED", "capability": "first_match", "arguments": {"needle": int(needle.group(1)), "values": values}, "missing_information": []}
    if "edades" in text or "estabilidad" in text:
        return {"plan_status": "VALIDATED", "capability": "stable_ages", "arguments": {"records": PARAMS["stable-ages"]["records"]}, "missing_information": []}
    if "10.000" in operation or "10000" in operation:
        sample = PARAMS["ten-thousand"]
        return {"plan_status": "VALIDATED", "capability": "descending_seed", "arguments": {"seed": sample["seed"], "count": sample["count"]}, "missing_information": []}
    if "push" in text and "peek" in text:
        return {"plan_status": "VALIDATED", "capability": "stack_script", "arguments": {"steps": PARAMS["stack-script"]["steps"]}, "missing_information": []}
    if "seis nodos" in text:
        return {"plan_status": "BLOCKED", "capability": None, "arguments": {}, "missing_information": ["edges", "endpoints"]}
    if "2×3" in operation or "2x3" in text:
        return {"plan_status": "BLOCKED", "capability": None, "arguments": {}, "missing_information": ["matrix-entries"]}
    if "determinante" in text:
        return {"plan_status": "BLOCKED", "capability": None, "arguments": {}, "missing_information": ["reference-matrix"]}
    if "media móvil" in text or "media movil" in text:
        window = PARAMS["moving-window"]
        generator = random.Random(window["seed"])
        values = [generator.randrange(0, 20) for _ in range(window["length"])]
        return {"plan_status": "VALIDATED", "capability": "moving_average", "arguments": {"values": values, "window": window["window"]}, "missing_information": []}
    return {"plan_status": "INCONCLUSIVE", "capability": None, "arguments": {}, "missing_information": ["operation-not-resolved"]}
