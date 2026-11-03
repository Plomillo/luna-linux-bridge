#!/usr/bin/env python3
"""Read-only ONNX anti-hallucination model probe; does not promote or rewrite weights."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

MODEL_BYTES = 110_516_001
MODEL_SHA256 = "c6a266fe0f7f1f782094ff4b1e7ae3547fa48a22ab44712881cc03bba07bc5b7"
TOKENIZER_GIT_BLOB_SHA1 = "a8d04251ca21a1682833a5891947a563880fd93d"


class ProbeError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    payload = Path(path).read_bytes()
    header = b"blob " + str(len(payload)).encode("ascii") + b"\\0"
    return hashlib.sha1(header + payload).hexdigest()


def _fixed_shape(shape: object, *, max_dim: int = 2048, sequence_length: int = 1) -> tuple[int, ...]:
    if not isinstance(shape, (list, tuple)):
        raise ProbeError("ONNX_INPUT_SHAPE_NOT_SEQUENCE")
    result = []
    for index, value in enumerate(shape):
        if isinstance(value, bool):
            raise ProbeError("ONNX_INPUT_SHAPE_BOOLEAN_DIMENSION")
        if isinstance(value, int):
            if value < 0 or value > max_dim:
                raise ProbeError("ONNX_INPUT_DIMENSION_OUT_OF_RANGE")
            result.append(value if value > 0 else (sequence_length if index == 1 and len(shape) > 1 else 1))
        else:
            result.append(sequence_length if index == 1 and len(shape) > 1 else 1)
    if math.prod(result or (1,)) > 2_000_000:
        raise ProbeError("ONNX_INPUT_TENSOR_ELEMENT_LIMIT")
    return tuple(result)


def _fit_vector(values: list[int], shape: tuple[int, ...], dtype, np):
    if not shape:
        return np.asarray(values[0] if values else 0, dtype=dtype)
    count = math.prod(shape)
    if count < 1:
        raise ProbeError("ONNX_INPUT_TENSOR_EMPTY_SHAPE")
    fitted = list(values[:count])
    if len(fitted) < count:
        fitted.extend([0] * (count - len(fitted)))
    return np.asarray(fitted, dtype=dtype).reshape(shape)


def _dtype_for_onnx(type_name: str, np):
    table = {
        "tensor(float)": np.float32,
        "tensor(float16)": np.float16,
        "tensor(double)": np.float64,
        "tensor(int64)": np.int64,
        "tensor(int32)": np.int32,
        "tensor(int16)": np.int16,
        "tensor(int8)": np.int8,
        "tensor(uint8)": np.uint8,
        "tensor(uint16)": np.uint16,
        "tensor(uint32)": np.uint32,
        "tensor(uint64)": np.uint64,
        "tensor(bool)": np.bool_,
    }
    if type_name not in table:
        raise ProbeError("ONNX_INPUT_TYPE_NOT_SUPPORTED:" + str(type_name))
    return table[type_name]


def _summarize_output(value, np) -> dict:
    array = np.asarray(value)
    row = {
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "elements": int(array.size),
    }
    if array.dtype.kind in "biufc":
        finite = np.isfinite(array)
        row["all_finite"] = bool(finite.all())
        if array.size and finite.all():
            flat = array.astype(np.float64, copy=False).reshape(-1)
            row.update({
                "minimum": float(flat.min()),
                "maximum": float(flat.max()),
                "mean": float(flat.mean()),
                "preview": [float(x) for x in flat[:12]],
            })
    elif array.dtype.kind in "OUS":
        row["preview"] = [str(x)[:120] for x in array.reshape(-1)[:8]]
    return row


def _make_feed(input_specs, encoding, np, *, max_sequence_length: int = 128) -> tuple[dict, list[str]]:
    feed = {}
    unknown = []
    ids = list(encoding.ids[:max_sequence_length])
    type_ids = list(encoding.type_ids[:max_sequence_length])
    sequence_length = max(1, len(ids))
    if not ids:
        raise ProbeError("TOKENIZER_RETURNED_NO_IDS")

    for spec in input_specs:
        name = str(spec.name)
        key = name.casefold()
        shape = _fixed_shape(spec.shape, sequence_length=sequence_length)
        dtype = _dtype_for_onnx(spec.type, np)

        if key in {"input_ids", "inputid", "tokens"}:
            values = ids
        elif key in {"attention_mask", "input_mask", "mask"}:
            values = [1] * len(ids)
        elif key in {"token_type_ids", "segment_ids"}:
            values = type_ids if type_ids else [0] * len(ids)
        elif key in {"position_ids", "positions"}:
            values = list(range(len(ids)))
        elif key in {"input_lengths", "sequence_length", "sequence_lengths"}:
            values = [len(ids)]
        else:
            # A deterministic zero tensor permits a graph-liveness probe only.
            # Unknown input semantics are explicitly retained in the report.
            values = [0]
            unknown.append(name)

        feed[name] = _fit_vector(values, shape, dtype, np)

    if not any(str(spec.name).casefold() in {"input_ids", "inputid", "tokens"} for spec in input_specs):
        raise ProbeError("ONNX_INPUT_IDS_NOT_REGISTERED")
    return feed, unknown


def probe_model(model_path: Path, tokenizer_path: Path, *, max_sequence_length: int = 128) -> dict:
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer

    model_path = Path(model_path)
    tokenizer_path = Path(tokenizer_path)
    for label, path in (("MODEL", model_path), ("TOKENIZER", tokenizer_path)):
        if path.is_symlink() or not path.is_file():
            raise ProbeError(label + "_FILE_MISSING_OR_UNSAFE")
    if model_path.stat().st_size != MODEL_BYTES:
        raise ProbeError("ANTI_HALLUCINATION_MODEL_SIZE_MISMATCH")
    model_sha = sha256_file(model_path)
    if model_sha != MODEL_SHA256:
        raise ProbeError("ANTI_HALLUCINATION_MODEL_SHA256_MISMATCH")
    tokenizer_sha = sha256_file(tokenizer_path)
    tokenizer_blob_sha1 = git_blob_sha1(tokenizer_path)
    if tokenizer_blob_sha1 != TOKENIZER_GIT_BLOB_SHA1:
        raise ProbeError("ANTI_HALLUCINATION_TOKENIZER_GIT_BLOB_SHA1_MISMATCH")
    if not 8 <= max_sequence_length <= 512:
        raise ProbeError("MAX_SEQUENCE_LENGTH_OUT_OF_RANGE")

    started = time.monotonic()
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    session = ort.InferenceSession(
        str(model_path),
        sess_options=options,
        providers=["CPUExecutionProvider"],
    )
    if "CPUExecutionProvider" not in session.get_providers():
        raise ProbeError("ONNX_CPU_PROVIDER_NOT_ACTIVE")

    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    metadata = session.get_modelmeta()
    input_specs = session.get_inputs()
    output_specs = session.get_outputs()
    if not input_specs or not output_specs:
        raise ProbeError("ONNX_GRAPH_INPUT_OR_OUTPUT_EMPTY")

    examples = [
        {
            "id": "supported_claim",
            "claim": "Water boils at 100 degrees Celsius at standard atmospheric pressure.",
            "evidence": "At one atmosphere of pressure, pure water has a boiling point of 100 degrees Celsius.",
        },
        {
            "id": "contradicted_claim",
            "claim": "The Earth is the largest planet in the Solar System.",
            "evidence": "Jupiter is the largest planet in the Solar System.",
        },
        {
            "id": "unsupported_claim",
            "claim": "The manuscript was written in the year 1427.",
            "evidence": "",
        },
    ]

    results = []
    has_unknown_inputs = False
    for example in examples:
        encoding = tokenizer.encode(example["claim"], example["evidence"] or None)
        feed, unknown = _make_feed(input_specs, encoding, np, max_sequence_length=max_sequence_length)
        has_unknown_inputs = has_unknown_inputs or bool(unknown)
        outputs = session.run(None, feed)
        if len(outputs) != len(output_specs):
            raise ProbeError("ONNX_OUTPUT_COUNT_MISMATCH")
        results.append({
            "example_id": example["id"],
            "token_count": len(encoding.ids),
            "unknown_zero_filled_inputs": unknown,
            "outputs": [
                {
                    "name": str(spec.name),
                    **_summarize_output(value, np),
                }
                for spec, value in zip(output_specs, outputs)
            ],
        })

    return {
        "schema": "LOUKSNAPG2_ANTI_HALLUCINATION_ONNX_PROBE/1.0",
        "status": "PASS_CPU_GRAPH_EXECUTION_ONLY",
        "model": {
            "path": model_path.as_posix(),
            "bytes": model_path.stat().st_size,
            "sha256": model_sha,
            "tokenizer_sha256": tokenizer_sha,
            "tokenizer_git_blob_sha1": tokenizer_blob_sha1,
        },
        "runtime": {
            "onnxruntime": ort.__version__,
            "numpy": np.__version__,
            "execution_provider": "CPUExecutionProvider",
            "intra_op_threads": 1,
            "inter_op_threads": 1,
        },
        "graph": {
            "producer_name": metadata.producer_name,
            "graph_name": metadata.graph_name,
            "domain": metadata.domain,
            "description": metadata.description[:1000],
            "custom_metadata": dict(metadata.custom_metadata_map or {}),
            "inputs": [
                {"name": str(x.name), "type": str(x.type), "shape": list(x.shape)}
                for x in input_specs
            ],
            "outputs": [
                {"name": str(x.name), "type": str(x.type), "shape": list(x.shape)}
                for x in output_specs
            ],
        },
        "probes": results,
        "input_contract_status": "PARTIAL_UNKNOWN_INPUTS_ZERO_FILLED" if has_unknown_inputs else "TOKENIZER_INPUT_BINDINGS_RECOGNIZED",
        "semantic_contract": "NOT_ESTABLISHED",
        "anti_hallucination_quality": "NOT_EVALUATED_NO_LABEL_MAPPING_OR_GOLDEN_SET",
        "route_registration": "NOT_PROMOTED",
        "source_model_mutated": False,
        "certification": "NOT_GRANTED",
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--tokenizer", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-sequence-length", type=int, default=128)
    args = parser.parse_args(argv)

    try:
        report = probe_model(args.model, args.tokenizer, max_sequence_length=args.max_sequence_length)
    except Exception as exc:
        report = {
            "schema": "LOUKSNAPG2_ANTI_HALLUCINATION_ONNX_PROBE/1.0",
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc)[:1000],
            "route_registration": "NOT_PROMOTED",
            "source_model_mutated": False,
            "certification": "NOT_GRANTED",
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report.get("status") == "PASS_CPU_GRAPH_EXECUTION_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
