#!/usr/bin/env python3
"""Pinned local Qwen3.5 4B S provider for REASONING_INTERFACE/1.0.

The provider is advisory only.  It verifies the exact F1 material binding before
every invocation, executes only a fixed llama-cli binary with shell=False, and
wraps model content in an authority-false LOUKSNA result envelope.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from interface import build_prompt, model_output_schema, validate_request, validate_result

PROVIDER_ID = "QWEN35_4B_S"
MANIFEST_PATH = HERE / "MODEL_MANIFEST.json"
BINDING_PATH = HERE / "F1_BINDING.json"


class ProviderHold(RuntimeError):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_binding():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    binding = json.loads(BINDING_PATH.read_text(encoding="utf-8"))
    if manifest.get("interface") != "REASONING_INTERFACE/1.0":
        raise ProviderHold("INTERFACE_BINDING_INVALID")
    if manifest.get("model", {}).get("provider_id") != PROVIDER_ID:
        raise ProviderHold("PROVIDER_ID_DRIFT")
    if binding.get("status") != "PASS":
        raise ProviderHold("F1_NOT_PASS")
    if binding.get("model", {}).get("sha256") != manifest.get("model", {}).get("expected_sha256"):
        raise ProviderHold("MODEL_HASH_BINDING_DRIFT")
    if binding.get("runtime", {}).get("source_revision") != manifest.get("runtime", {}).get("revision"):
        raise ProviderHold("RUNTIME_REVISION_BINDING_DRIFT")
    return manifest, binding


def material_paths(binding):
    model = Path(binding["model"]["path"]).expanduser()
    runtime = Path(binding["runtime"]["path"]).expanduser()
    return model, runtime


def verify_material():
    manifest, binding = load_binding()
    model, runtime = material_paths(binding)
    for path, label in ((model, "MODEL"), (runtime, "RUNTIME")):
        if path.is_symlink() or not path.is_file():
            raise ProviderHold(label + "_MATERIAL_INVALID")
        if path.stat().st_uid != os.getuid():
            raise ProviderHold(label + "_OWNER_INVALID")
    if model.stat().st_size != binding["model"]["bytes"]:
        raise ProviderHold("MODEL_BYTES_MISMATCH")
    if sha256_file(model) != binding["model"]["sha256"]:
        raise ProviderHold("MODEL_SHA256_MISMATCH")
    if sha256_file(runtime) != binding["runtime"]["binary_sha256"]:
        raise ProviderHold("RUNTIME_SHA256_MISMATCH")
    if not os.access(runtime, os.X_OK):
        raise ProviderHold("RUNTIME_NOT_EXECUTABLE")
    return manifest, binding, model, runtime


def _extract_json(text):
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    first = text.find("{")
    last = text.rfind("}")
    if first >= 0 and last > first:
        try:
            return json.loads(text[first:last + 1])
        except Exception:
            pass
    raise ProviderHold("MODEL_OUTPUT_NOT_JSON")


def invoke(request, timeout_sec=180, threads=2, ctx_size=3072, reasoning_budget=256):
    request = validate_request(request)
    _manifest, binding, model, runtime = verify_material()
    schema = json.dumps(model_output_schema(), separators=(",", ":"))
    prompt = build_prompt(request)
    cmd = [
        str(runtime),
        "-m", str(model),
        "-p", prompt,
        "-n", "512",
        "--temp", "0",
        "--ctx-size", str(ctx_size),
        "--threads", str(threads),
        "--no-display-prompt",
        "--simple-io",
        "--single-turn",
        "--reasoning-budget", str(reasoning_budget),
        "--reasoning-format", "deepseek",
        "--json-schema", schema,
    ]
    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec,
            check=False,
            shell=False,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except subprocess.TimeoutExpired as exc:
        raise ProviderHold("MODEL_TIMEOUT") from exc
    if proc.returncode != 0:
        raise ProviderHold("MODEL_RUNTIME_FAILED:" + str(proc.returncode))
    try:
        obj = _extract_json(proc.stdout)
    except ProviderHold:
        if diagnostic_dir is not None:
            print("LOUKSNA_REASONING_DIAG_STDOUT=" + repr(proc.stdout[:4000]), file=sys.stderr)
            print("LOUKSNA_REASONING_DIAG_STDERR_TAIL=" + repr(proc.stderr[-4000:]), file=sys.stderr)
        raise
    result = validate_result(obj, request["request_id"], PROVIDER_ID)
    result["material_binding"] = {
        "model_sha256": binding["model"]["sha256"],
        "runtime_sha256": binding["runtime"]["binary_sha256"],
        "f1_run_id": binding["f1_run_id"],
    }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, help="Path to LOUKSNA_REASONING_REQUEST/1.0 JSON")
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout-sec", type=int, default=180)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--ctx-size", type=int, default=3072)
    parser.add_argument("--reasoning-budget", type=int, default=256)
    args = parser.parse_args(argv)
    request = json.loads(Path(args.request).read_text(encoding="utf-8"))
    result = invoke(
        request,
        timeout_sec=args.timeout_sec,
        threads=args.threads,
        ctx_size=args.ctx_size,
        reasoning_budget=args.reasoning_budget,
    )
    out = Path(args.out)
    out.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "schema": result["schema"],
        "request_id": result["request_id"],
        "provider_id": result["provider_id"],
        "execution_allowed": result["execution_allowed"],
        "result_sha256": result["result_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
