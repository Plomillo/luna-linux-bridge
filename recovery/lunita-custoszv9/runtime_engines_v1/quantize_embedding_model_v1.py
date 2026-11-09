#!/usr/bin/env python3
"""Quantize the cached E04 ONNX model only when semantic regression gates pass.

The source model remains in the FastEmbed registry identity. The generated
INT8 ONNX is a candidate binary; it is accepted only after:
- ONNX structural validation,
- real FastEmbed inference on a fixed multilingual Spanish corpus,
- per-vector cosine similarity thresholds,
- identical top-1 retrieval decisions for every registered query,
- a material file-size reduction.
Failure restores the original ONNX file byte-for-byte.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any

MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIMENSION = 384
MIN_MEAN_COSINE = 0.995
MIN_VECTOR_COSINE = 0.985
REQUIRED_RETRIEVAL_AGREEMENT = 1.0
MAX_QUANTIZED_SIZE_RATIO = 0.60

DOCUMENTS = [
    "La protección del agua potable exige conservar las cuencas hidrográficas y sus ecosistemas.",
    "La astronomía estudia planetas, estrellas, galaxias y la evolución del universo observable.",
    "El fútbol organiza equipos, estrategias tácticas, entrenamientos y campeonatos deportivos.",
    "La psicología cognitiva investiga memoria, atención, aprendizaje y procesos de razonamiento.",
    "La economía analiza inflación, empleo, mercados financieros, producción y consumo.",
    "La historia examina documentos, sociedades, acontecimientos y transformaciones culturales.",
    "La lingüística estudia gramática, sintaxis, semántica y traducción entre idiomas.",
    "La gastronomía desarrolla recetas, técnicas de cocina, ingredientes y conservación de alimentos.",
    "La ciberseguridad protege redes, sistemas operativos, identidades y datos frente a ataques.",
    "La biología investiga células, genética, evolución y diversidad de organismos.",
]
QUERIES = [
    "proteger el agua potable y las cuencas",
    "estudio de galaxias y planetas",
    "tácticas de los equipos de fútbol",
    "memoria y atención en el aprendizaje",
    "inflación del mercado y economía",
    "transformaciones de las sociedades en la historia",
    "gramática y traducción de idiomas",
    "preparación de recetas y alimentos",
    "defensa de redes y sistemas informáticos",
    "genética y evolución de los seres vivos",
]


class QuantizationError(RuntimeError):
    pass


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise QuantizationError("Embedding dimensions differ or are empty")
    dot = sum(a * b for a, b in zip(left, right))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    if norm_left == 0 or norm_right == 0:
        raise QuantizationError("Zero-norm embedding is not valid for cosine comparison")
    return dot / (norm_left * norm_right)


def embedding_probe(cache: pathlib.Path, pythonpath: str, texts: list[str]) -> list[list[float]]:
    source = r'''
import json, os, sys
from fastembed import TextEmbedding
cache = sys.argv[1]
texts = json.loads(sys.argv[2])
engine = TextEmbedding(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    cache_dir=cache, threads=1, mmap=True,
)
vectors = [[float(v) for v in row.tolist()] for row in engine.embed(texts)]
print(json.dumps(vectors, separators=(",", ":")))
'''
    env = os.environ.copy()
    env["PYTHONPATH"] = pythonpath + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["LUNITA_FASTEMBED_CACHE"] = str(cache)
    env["HF_HOME"] = str(cache)
    env["HF_HUB_CACHE"] = str(cache / "hub")
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", source, str(cache), json.dumps(texts, ensure_ascii=False)],
        env=env, capture_output=True, text=True, timeout=300, check=False,
    )
    if result.returncode != 0:
        raise QuantizationError("FastEmbed inference failed: " + (result.stderr or result.stdout)[-1800:])
    vectors = json.loads(result.stdout)
    if len(vectors) != len(texts) or any(len(vector) != DIMENSION for vector in vectors):
        raise QuantizationError("FastEmbed returned a wrong vector count or dimension")
    return vectors


def find_onnx_model(cache: pathlib.Path) -> pathlib.Path:
    matches = sorted(cache.glob(
        "models--Qdrant--paraphrase-multilingual-MiniLM-L12-v2-onnx-Q/snapshots/*/model_optimized.onnx"
    ))
    if len(matches) != 1:
        raise QuantizationError(f"Expected one pinned E04 ONNX model; found {len(matches)}")
    path = matches[0]
    if path.is_symlink() or not path.is_file():
        raise QuantizationError("E04 model must be a regular materialized file")
    return path


def quantize_model(model: pathlib.Path, output: pathlib.Path, pythonpath: str) -> dict[str, Any]:
    source = r'''
import json, re, sys
import onnx
import onnxruntime as ort
from onnx import checker, TensorProto
from onnxruntime.quantization import QuantType, quantize_dynamic

model_in, model_out = sys.argv[1], sys.argv[2]
quantize_dynamic(
    model_input=model_in,
    model_output=model_out,
    weight_type=QuantType.QInt8,
    per_channel=True,
    reduce_range=False,
)

graph = onnx.load(model_out, load_external_data=True)
if not graph.graph.node or not graph.graph.input or not graph.graph.output:
    raise RuntimeError("Quantized ONNX graph has missing nodes, inputs, or outputs")

opset_imports = {item.domain or "ai.onnx": int(item.version) for item in graph.opset_import}
default_opset = opset_imports.get("ai.onnx")
layer_norm_nodes = [
    {"name": node.name, "domain": node.domain or "ai.onnx"}
    for node in graph.graph.node if node.op_type == "LayerNormalization"
]
int8_initializers = [
    initializer.name for initializer in graph.graph.initializer
    if initializer.data_type == TensorProto.INT8
]
quantized_operators = [
    node.op_type for node in graph.graph.node
    if node.op_type in {
        "MatMulInteger", "DynamicQuantizeLinear", "QLinearMatMul",
        "QLinearConv", "QuantizeLinear", "DequantizeLinear",
    }
]
try:
    checker.check_model(graph, full_check=True)
    checker_status = "PASS_ONNX_CHECKER"
    checker_error = None
except Exception as exc:
    checker_error = f"{type(exc).__name__}: {exc}"
    known_compatibility_gap = (
        default_opset == 11
        and bool(layer_norm_nodes)
        and "No Op registered for LayerNormalization with domain_version of 11" in str(exc)
        and all(node["domain"] == "ai.onnx" for node in layer_norm_nodes)
    )
    if not known_compatibility_gap:
        raise
    checker_status = "KNOWN_ONNX_SCHEMA_REGISTRY_GAP_LAYER_NORMALIZATION_OPSET11"

if not int8_initializers:
    raise RuntimeError("Quantized model contains no INT8 initializer tensors")
if not quantized_operators:
    raise RuntimeError("Quantized model contains no quantized ONNX operators")

# The standard ONNX schema registry in the pinned checker does not know this
# model's legacy LayerNormalization declaration. Require ONNX Runtime itself to
# load the complete candidate graph, then FastEmbed performs actual inference
# and semantic comparison in a fresh process in the parent pipeline.
session = ort.InferenceSession(model_out, providers=["CPUExecutionProvider"])
inputs = session.get_inputs()
outputs = session.get_outputs()
if not inputs or not outputs:
    raise RuntimeError("ONNX Runtime candidate session has no inputs or outputs")

report = {
    "checker_status": checker_status,
    "checker_error": checker_error,
    "opset_imports": opset_imports,
    "layer_normalization_node_count": len(layer_norm_nodes),
    "int8_initializer_count": len(int8_initializers),
    "int8_initializer_names_sha256": __import__("hashlib").sha256(
        "\n".join(int8_initializers).encode("utf-8")
    ).hexdigest(),
    "quantized_operator_counts": {
        name: sum(1 for value in quantized_operators if value == name)
        for name in sorted(set(quantized_operators))
    },
    "onnxruntime_load_status": "PASS",
    "onnxruntime_provider": session.get_providers()[0],
    "input_names": [item.name for item in inputs],
    "output_names": [item.name for item in outputs],
}
print(json.dumps(report, sort_keys=True, separators=(",", ":")))
'''
    env = os.environ.copy()
    env["PYTHONPATH"] = pythonpath + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    result = subprocess.run(
        [sys.executable, "-c", source, str(model), str(output)],
        env=env, capture_output=True, text=True, timeout=900, check=False,
    )
    if result.returncode != 0 or not output.is_file():
        raise QuantizationError("ONNX Runtime INT8 quantization/validation failed: " + (result.stderr or result.stdout)[-3000:])
    try:
        report = json.loads(result.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise QuantizationError("ONNX Runtime quantization validation did not emit a valid JSON receipt") from exc
    if report.get("onnxruntime_load_status") != "PASS" or not report.get("int8_initializer_count"):
        raise QuantizationError("INT8 candidate did not pass structural/runtime validation")
    return report


def run(cache: pathlib.Path, pythonpath: str) -> dict[str, Any]:
    model = find_onnx_model(cache)
    receipt_path = cache / "LUNITA_E04_ONNX_QUANTIZATION_RECEIPT.json"
    if receipt_path.exists():
        raise QuantizationError("E04 quantization receipt already exists; overwrite is forbidden")
    original_sha = sha256_file(model)
    original_size = model.stat().st_size
    all_texts = DOCUMENTS + QUERIES

    # Baseline must run before the candidate file is created or installed.
    baseline = embedding_probe(cache, pythonpath, all_texts)
    with tempfile.TemporaryDirectory(prefix="lunita-e04-int8-") as temporary:
        root = pathlib.Path(temporary)
        quantized = root / "model_optimized.int8.onnx"
        backup = root / "model_optimized.float32.onnx"
        shutil.copy2(model, backup)
        onnx_validation = quantize_model(model, quantized, pythonpath)
        quantized_size = quantized.stat().st_size
        if quantized_size >= original_size * MAX_QUANTIZED_SIZE_RATIO:
            raise QuantizationError(
                f"INT8 model did not meet size-reduction target: {quantized_size}/{original_size}"
            )
        # Replace one candidate cache file, then execute a fresh FastEmbed process.
        os.replace(quantized, model)
        try:
            candidate = embedding_probe(cache, pythonpath, all_texts)
            vector_cosines = [cosine(a, b) for a, b in zip(baseline, candidate)]
            if len(vector_cosines) != len(all_texts):
                raise QuantizationError("Embedding comparison vector count mismatch")
            mean_cosine = sum(vector_cosines) / len(vector_cosines)
            minimum_cosine = min(vector_cosines)

            docs_base = baseline[:len(DOCUMENTS)]
            docs_quant = candidate[:len(DOCUMENTS)]
            queries_base = baseline[len(DOCUMENTS):]
            queries_quant = candidate[len(DOCUMENTS):]
            decisions = []
            for index, (query_base, query_quant) in enumerate(zip(queries_base, queries_quant)):
                scores_base = [cosine(query_base, doc) for doc in docs_base]
                scores_quant = [cosine(query_quant, doc) for doc in docs_quant]
                rank_base = sorted(range(len(scores_base)), key=lambda i: scores_base[i], reverse=True)
                rank_quant = sorted(range(len(scores_quant)), key=lambda i: scores_quant[i], reverse=True)
                decisions.append({
                    "query_index": index,
                    "baseline_top1": rank_base[0],
                    "int8_top1": rank_quant[0],
                    "top1_match": rank_base[0] == rank_quant[0],
                    "baseline_top3": rank_base[:3],
                    "int8_top3": rank_quant[:3],
                })
            agreement = sum(item["top1_match"] for item in decisions) / len(decisions)
            if mean_cosine < MIN_MEAN_COSINE:
                raise QuantizationError(f"Mean cosine {mean_cosine:.6f} is below {MIN_MEAN_COSINE}")
            if minimum_cosine < MIN_VECTOR_COSINE:
                raise QuantizationError(f"Minimum cosine {minimum_cosine:.6f} is below {MIN_VECTOR_COSINE}")
            if agreement < REQUIRED_RETRIEVAL_AGREEMENT:
                raise QuantizationError(
                    f"Retrieval top-1 agreement {agreement:.3f} is below {REQUIRED_RETRIEVAL_AGREEMENT:.3f}"
                )
            quantized_sha = sha256_file(model)
            receipt = {
                "schema": "LUNITA_E04_ONNX_QUANTIZATION/1.0",
                "status": "PASS_INT8_QUANTIZATION_MEASURED",
                "model_id": MODEL_ID,
                "model_file": "model_optimized.onnx",
                "model_cache_relative_path": model.relative_to(cache).as_posix(),
                "quantization": "ONNX_RUNTIME_DYNAMIC_QINT8_PER_CHANNEL",
                "original_sha256": original_sha,
                "quantized_sha256": quantized_sha,
                "original_bytes": original_size,
                "quantized_bytes": quantized_size,
                "size_ratio": quantized_size / original_size,
                "onnx_validation": onnx_validation,
                "mean_vector_cosine": mean_cosine,
                "minimum_vector_cosine": minimum_cosine,
                "retrieval_top1_agreement": agreement,
                "corpus_document_count": len(DOCUMENTS),
                "query_count": len(QUERIES),
                "embedding_dimension": DIMENSION,
                "thresholds": {
                    "minimum_mean_vector_cosine": MIN_MEAN_COSINE,
                    "minimum_vector_cosine": MIN_VECTOR_COSINE,
                    "required_retrieval_top1_agreement": REQUIRED_RETRIEVAL_AGREEMENT,
                    "maximum_model_size_ratio": MAX_QUANTIZED_SIZE_RATIO,
                },
                "retrieval_decisions": decisions,
                "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                "certification": "NOT_GRANTED",
            }
            payload = json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            receipt_temp = cache / f".{receipt_path.name}.{os.getpid()}.tmp"
            fd = os.open(receipt_temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            try:
                view = memoryview(payload.encode("utf-8"))
                while view:
                    written = os.write(fd, view)
                    if written <= 0:
                        raise OSError("Short write while persisting E04 quantization receipt")
                    view = view[written:]
                os.fsync(fd)
            except Exception:
                receipt_temp.unlink(missing_ok=True)
                raise
            finally:
                os.close(fd)
            try:
                os.link(receipt_temp, receipt_path)
            except Exception:
                receipt_temp.unlink(missing_ok=True)
                raise
            receipt_temp.unlink()
            return receipt
        except Exception:
            shutil.copy2(backup, model)
            if sha256_file(model) != original_sha:
                raise QuantizationError("E04 rollback failed to restore the exact original ONNX model digest")
            raise


def main() -> int:
    cache = pathlib.Path(os.environ["LUNITA_FASTEMBED_CACHE"]).resolve(strict=True)
    pythonpath = os.environ["PYTHONPATH"]
    receipt = run(cache, pythonpath)
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({
            "schema": "LUNITA_E04_ONNX_QUANTIZATION/1.0",
            "status": "BLOCKED_E04_QUANTIZATION",
            "error_type": type(exc).__name__,
            "error": str(exc)[:2400],
            "certification": "NOT_GRANTED",
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(2)
