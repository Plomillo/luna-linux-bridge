#!/usr/bin/env python3
"""Governed GPU-stack preflight for LouksnapG2 model repair.

This program never trains, rewrites source weights, or promotes a candidate.
It records whether the selected target is eligible to enter a separately
implemented repair adapter. Missing prerequisites fail closed.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "LOUKSNAPG2_GPU_PREFLIGHT_EVIDENCE/1.1"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN_HUB_CREDENTIALS = ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACEHUB_API_TOKEN")


def load_matrix(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "repair" / "gpu" / "target-matrix-v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "LOUKSNAPG2_GPU_REPAIR_TARGET_MATRIX/1.0":
        raise ValueError("GPU_TARGET_MATRIX_SCHEMA_INVALID")
    targets = data.get("targets")
    if not isinstance(targets, dict) or len(targets) != 5:
        raise ValueError("GPU_TARGET_MATRIX_MUST_DECLARE_FIVE_MODELS")
    governance = data.get("governance", {})
    if governance.get("original_weights_mutable") is not False:
        raise ValueError("ORIGINAL_WEIGHT_MUTATION_POLICY_INVALID")
    if governance.get("global_distribution_limit_bytes") != 490000000:
        raise ValueError("GLOBAL_DISTRIBUTION_CAP_DRIFT")
    return data


def repair_gate(spec: dict[str, Any], source_revision: str, dataset_id: str,
                dataset_revision: str) -> list[str]:
    blockers: list[str] = []
    if spec.get("adapter_status") != "IMPLEMENTED_AND_TESTED":
        blockers.append("REPAIR_ADAPTER_NOT_IMPLEMENTED_AND_TESTED")
    if not SHA_RE.fullmatch(source_revision or ""):
        blockers.append("SOURCE_REVISION_NOT_PINNED_TO_40_HEX_SHA")
    if not dataset_id or not dataset_id.strip():
        blockers.append("TRAINING_DATASET_ID_MISSING")
    if not SHA_RE.fullmatch(dataset_revision or ""):
        blockers.append("TRAINING_DATASET_REVISION_NOT_PINNED_TO_40_HEX_SHA")
    return blockers


def command_output(command: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        proc = subprocess.run(command, capture_output=True, text=True,
                              timeout=timeout, check=False)
        return proc.returncode, (proc.stdout or proc.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, type(exc).__name__


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def probe_runtime() -> dict[str, Any]:
    report: dict[str, Any] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": {
            "torch": package_version("torch"),
            "transformers": package_version("transformers"),
            "megatron-bridge": package_version("megatron-bridge"),
            "nvidia-modelopt": package_version("nvidia-modelopt"),
        },
        "imports": {},
        "cuda_available": False,
        "gpu_count": 0,
        "gpus": [],
    }
    for module_name in ("torch", "transformers", "megatron.bridge"):
        try:
            importlib.import_module(module_name)
            report["imports"][module_name] = "PASS"
        except Exception as exc:
            report["imports"][module_name] = (
                "FAIL:" + type(exc).__name__ + ":" + str(exc)[:400]
            )
    try:
        import torch
        report["cuda_available"] = bool(torch.cuda.is_available())
        report["torch_cuda_version"] = torch.version.cuda
        report["gpu_count"] = int(torch.cuda.device_count())
        for index in range(report["gpu_count"]):
            prop = torch.cuda.get_device_properties(index)
            report["gpus"].append({
                "index": index,
                "name": prop.name,
                "total_memory_bytes": int(prop.total_memory),
                "total_memory_gib": round(prop.total_memory / (1024 ** 3), 2),
                "compute_capability": f"{prop.major}.{prop.minor}",
            })
    except Exception as exc:
        report["torch_probe_error"] = type(exc).__name__ + ":" + str(exc)[:400]
    nvidia_rc, nvidia_text = command_output([
        "nvidia-smi", "--query-gpu=name,memory.total,driver_version",
        "--format=csv,noheader",
    ])
    report["nvidia_smi_exit_code"] = nvidia_rc
    report["nvidia_smi"] = nvidia_text
    report["forbidden_hub_credential_names_present"] = sorted(
        name for name in FORBIDDEN_HUB_CREDENTIALS if os.environ.get(name, "").strip()
    )
    return report


def evaluate_hardware(spec: dict[str, Any], runtime: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if runtime.get("forbidden_hub_credential_names_present"):
        blockers.append("HUGGING_FACE_CREDENTIALS_FORBIDDEN_BY_PROVIDER_POLICY")
    imports = runtime.get("imports", {})
    if imports.get("torch") != "PASS":
        blockers.append("PYTORCH_IMPORT_FAILED")
    if imports.get("transformers") != "PASS":
        blockers.append("TRANSFORMERS_IMPORT_FAILED")
    if not runtime.get("cuda_available") or runtime.get("gpu_count", 0) < 1:
        blockers.append("CUDA_GPU_NOT_VISIBLE")
    if runtime.get("nvidia_smi_exit_code") != 0:
        blockers.append("NVIDIA_SMI_UNAVAILABLE")
    minimum_gpus = int(spec.get("minimum_gpus", 1))
    if runtime.get("gpu_count", 0) < minimum_gpus:
        blockers.append(f"GPU_COUNT_BELOW_TARGET_MINIMUM:{minimum_gpus}")
    minimum_vram = spec.get("minimum_vram_gib_per_gpu")
    if minimum_vram is not None:
        observed = [gpu.get("total_memory_gib", 0) for gpu in runtime.get("gpus", [])]
        if len(observed) < minimum_gpus or any(
            value < float(minimum_vram) for value in observed[:minimum_gpus]
        ):
            blockers.append(f"GPU_VRAM_BELOW_TARGET_MINIMUM_GIB:{minimum_vram}")
    if spec.get("framework") == "NVIDIA NeMo Megatron Bridge":
        if imports.get("megatron.bridge") != "PASS":
            blockers.append("MEGATRON_BRIDGE_IMPORT_FAILED")
    return blockers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--mode", choices=("preflight", "repair"), default="preflight")
    parser.add_argument("--source-revision", default="")
    parser.add_argument("--dataset-id", default="")
    parser.add_argument("--dataset-revision", default="")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve(strict=True)
    matrix = load_matrix(repo_root)
    if args.target not in matrix["targets"]:
        raise SystemExit("UNKNOWN_REPAIR_TARGET:" + args.target)
    spec = matrix["targets"][args.target]
    runtime = probe_runtime()
    hardware_blockers = evaluate_hardware(spec, runtime)
    repair_blockers = repair_gate(
        spec, args.source_revision, args.dataset_id, args.dataset_revision
    )
    report = {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z"),
        "source_commit": os.environ.get("GITHUB_SHA", "UNKNOWN"),
        "target": args.target,
        "model_id": spec["model_id"],
        "framework": spec["framework"],
        "provider_policy": matrix["governance"]["provider_policy"],
        "model_artifact_source_policy": matrix["governance"]["provider_policy"]["model_artifact_source"],
        "dataset_source_policy": matrix["governance"]["provider_policy"]["dataset_source"],
        "hugging_face_platform_used": False,
        "network_model_download_performed": False,
        "container_image": os.environ.get(
            "LOUKSNAPG2_CONTAINER_IMAGE", "nvcr.io/nvidia/nemo:26.06"
        ),
        "container_image_id": os.environ.get(
            "LOUKSNAPG2_CONTAINER_IMAGE_ID", "UNAVAILABLE"
        ),
        "mode": args.mode,
        "runtime": runtime,
        "hardware_blockers": hardware_blockers,
        "repair_blockers": repair_blockers,
        "adapter_status": spec.get("adapter_status"),
        "source_revision": args.source_revision or None,
        "training_dataset_id": args.dataset_id or None,
        "training_dataset_revision": args.dataset_revision or None,
        "original_weights_mutated": False,
        "training_executed": False,
        "candidate_written": False,
        "canonical_promotion": "NOT_AUTHORIZED",
        "global_certification": "NOT_GRANTED",
        "distribution_cap_bytes": matrix["governance"]["global_distribution_limit_bytes"],
    }
    if hardware_blockers:
        report["status"] = "PREFLIGHT_FAIL_CLOSED"
    elif args.mode == "repair" and repair_blockers:
        report["status"] = "REPAIR_BLOCKED_FAIL_CLOSED"
    elif args.mode == "repair":
        report["status"] = "REPAIR_ADAPTER_DISPATCH_NOT_CONFIGURED"
        report["repair_blockers"].append(
            "NO_EXECUTABLE_MODEL_REPAIR_DISPATCHER_REGISTERED"
        )
    else:
        report["status"] = "GPU_STACK_PREFLIGHT_PASS_REPAIR_HOLD"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    if hardware_blockers:
        return 2
    if args.mode == "repair" and report["status"] != "REPAIR_ADAPTER_DISPATCH_NOT_CONFIGURED":
        return 3
    if args.mode == "repair":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
