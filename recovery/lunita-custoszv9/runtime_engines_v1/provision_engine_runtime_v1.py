#!/usr/bin/env python3
"""Provision pinned E02-E15 dependencies into the additive Lunita overlay only.

Must be invoked in the target-compatible Python 3.12 environment by the
authorized worker. It never installs into the host/global site-packages.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

OWL_RL_SHA256 = "83347bf7f133979e87b2b18695d51d25510b99cec3f6919b5df05d4fbf058ae0"
OWL_RL_VERSION = "7.6.2"


class ProvisionError(RuntimeError):
    pass


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(argv: list[str], env: dict[str, str]) -> str:
    result = subprocess.run(argv, env=env, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise ProvisionError(f"Command failed ({result.returncode}): {' '.join(argv)}\n{result.stderr[-3000:]}")
    return result.stdout


def provision(overlay: pathlib.Path, python: pathlib.Path, model_cache: pathlib.Path) -> dict:
    overlay = overlay.resolve(strict=True)
    if not (overlay / "OVERLAY_APPLY_RECEIPT.json").is_file():
        raise ProvisionError("Additive overlay apply receipt missing")
    apply_receipt = json.loads((overlay / "OVERLAY_APPLY_RECEIPT.json").read_text(encoding="utf-8"))
    if apply_receipt.get("status") != "APPLIED_ADDITIVELY_NOT_CERTIFIED":
        raise ProvisionError("Overlay is not an accepted additive install")
    if apply_receipt.get("certification") != "NOT_GRANTED":
        raise ProvisionError("Unexpected overlay certification state")
    if not python.is_file() or not os.access(python, os.X_OK):
        raise ProvisionError("Target Python interpreter is not executable")
    version = run([str(python), "-c", "import sys; print('.'.join(map(str, sys.version_info[:2])))"], os.environ.copy()).strip()
    if version != "3.12":
        raise ProvisionError(f"Target Python must be 3.12, found {version}")
    site = overlay / "vendor/python3.12/site-packages"
    site.mkdir(parents=True, exist_ok=False)
    model_cache.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(site)
    env["LUNITA_ENGINE_DIR"] = str(overlay)
    env["LUNITA_FASTEMBED_CACHE"] = str(model_cache / "fastembed")
    env["LUNITA_VECTOR_DB_PATH"] = str(model_cache / "qdrant")
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"

    requirements = overlay / "requirements-engine-stack.txt"
    run([str(python), "-m", "pip", "install", "--disable-pip-version-check",
         "--only-binary=:all:", "--no-compile", "--target", str(site), "-r", str(requirements)], env)
    with tempfile.TemporaryDirectory(prefix="lunita-owlrl-") as temporary:
        wheel_dir = pathlib.Path(temporary)
        run([str(python), "-m", "pip", "download", "--disable-pip-version-check", "--no-deps",
             "--only-binary=:all:", "--dest", str(wheel_dir), f"owlrl=={OWL_RL_VERSION}"], env)
        wheels = list(wheel_dir.glob(f"owlrl-{OWL_RL_VERSION}-*.whl"))
        if len(wheels) != 1:
            raise ProvisionError(f"Expected one OWL-RL wheel, found {len(wheels)}")
        wheel_hash = sha256_file(wheels[0])
        if wheel_hash != OWL_RL_SHA256:
            raise ProvisionError(f"OWL-RL wheel hash mismatch: {wheel_hash}")
        run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "--no-deps",
             "--no-compile", "--target", str(site), str(wheels[0])], env)

    env["PYTHONPATH"] = str(site)
    smoke = r'''
import json
import os
import sys
from pathlib import Path
from fastembed import TextEmbedding
import qdrant_client, rdflib, owlrl, jsonschema, onnxruntime, numpy
sys.path.insert(0, os.environ["LUNITA_ENGINE_DIR"])
from engine_runtime_v1 import nlp_analyze, build_knowledge_graph, formalize_expression
cache = os.environ["LUNITA_FASTEMBED_CACHE"]
Path(cache).mkdir(parents=True, exist_ok=True)
nlp = nlp_analyze("Lunita valida la evidencia y preserva la procedencia.")
assert len(nlp["tokens"]) >= 6 and nlp["engine_id"] == "E02"
graph = build_knowledge_graph([{"id":"a"},{"id":"b"}],[{"source":"a","target":"b","relation":"supports"}])
assert graph["graph"].shortest_path("a","b") == ["a","b"]
formal = formalize_expression({"op":"add","args":[{"number":0.5},{"number":0.5},{"symbol":"x"}]})
assert formal["simplified"] == "add(1,x)"
embedder = TextEmbedding(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", cache_dir=cache, threads=1, mmap=True)
vectors = list(embedder.embed(["Lunita conserva el contexto"]))
assert len(vectors) == 1 and len(vectors[0]) == 384
print(json.dumps({"E02":"PASS","E04":"PASS","E06":"PASS","E12":"PASS",
 "embedding_dimension":384,"qdrant":qdrant_client.__version__,
 "rdflib":rdflib.__version__,"owlrl":"PASS","jsonschema":jsonschema.__version__,
 "onnxruntime":onnxruntime.__version__,"numpy":numpy.__version__},sort_keys=True))
'''
    output = run([str(python), "-c", smoke], env)
    receipt = {
        "schema": "LUNITA_ENGINE_DEPENDENCY_PROVISION_RECEIPT/1.0",
        "status": "DEPENDENCIES_PROVISIONED_NOT_CERTIFIED",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": version,
        "overlay": str(overlay),
        "site_packages": str(site),
        "model_cache": str(model_cache),
        "requirements_sha256": sha256_file(requirements),
        "owlrl_wheel_sha256": wheel_hash,
        "smoke_output": output.strip(),
        "certification": "NOT_GRANTED",
    }
    receipt_path = overlay / "DEPENDENCY_PROVISION_RECEIPT.json"
    if receipt_path.exists():
        raise ProvisionError("Provision receipt already exists; overwrite is forbidden")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overlay", required=True, type=pathlib.Path)
    parser.add_argument("--python", required=True, type=pathlib.Path)
    parser.add_argument("--model-cache", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = provision(args.overlay, args.python, args.model_cache)
    except (OSError, ValueError, ProvisionError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
