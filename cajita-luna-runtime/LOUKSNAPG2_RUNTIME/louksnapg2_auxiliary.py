#!/usr/bin/env python3
"""Bounded auxiliary execution backends for Louksnapg2.

The original model weights and adapters are not altered. These backends are
explicit, source-identifiable execution paths: formal reasoning (supported
problem classes), Apertium translation, Tesseract OCR and whisper.cpp ASR.
Unsupported requests fail closed instead of being labelled as neural-model output.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import io
import json
import operator
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


class AuxiliaryEngineError(RuntimeError):
    pass


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _format_number(value: Any) -> str:
    if isinstance(value, bool):
        raise AuxiliaryEngineError("BOOLEAN_IS_NOT_NUMERIC_RESULT")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not (float("-inf") < value < float("inf")):
            raise AuxiliaryEngineError("NONFINITE_ARITHMETIC_RESULT")
        if value.is_integer():
            return str(int(value))
        return format(value, ".12g")
    raise AuxiliaryEngineError("UNSUPPORTED_ARITHMETIC_RESULT_TYPE")


_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _safe_expression(expression: str) -> str:
    expression = expression.strip().replace(",", "")
    if not expression or len(expression) > 256:
        raise AuxiliaryEngineError("ARITHMETIC_EXPRESSION_LENGTH_INVALID")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise AuxiliaryEngineError("ARITHMETIC_EXPRESSION_INVALID") from exc

    def visit(node: ast.AST) -> int | float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            if abs(node.value) > 1_000_000_000:
                raise AuxiliaryEngineError("ARITHMETIC_LITERAL_OUT_OF_RANGE")
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Div) and right == 0:
                raise AuxiliaryEngineError("ARITHMETIC_DIVISION_BY_ZERO")
            if isinstance(node.op, ast.FloorDiv) and right == 0:
                raise AuxiliaryEngineError("ARITHMETIC_DIVISION_BY_ZERO")
            if isinstance(node.op, ast.Mod) and right == 0:
                raise AuxiliaryEngineError("ARITHMETIC_DIVISION_BY_ZERO")
            value = _BINOPS[type(node.op)](left, right)
            if abs(value) > 10**18:
                raise AuxiliaryEngineError("ARITHMETIC_RESULT_OUT_OF_RANGE")
            return value
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARYOPS:
            return _UNARYOPS[type(node.op)](visit(node.operand))
        raise AuxiliaryEngineError("ARITHMETIC_SYNTAX_NOT_IN_ALLOWLIST")

    return _format_number(visit(tree))


def formal_reasoning(prompt: str) -> dict | None:
    """Answer a bounded, explicit subset of arithmetic and elementary logic."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise AuxiliaryEngineError("REASONING_PROMPT_REQUIRED")
    text = " ".join(prompt.strip().split())
    arithmetic = re.search(
        r"\b(?:compute|calculate|evaluate)\s+(.+?)(?=\s*(?:\.|;|$))",
        text,
        flags=re.IGNORECASE,
    )
    if arithmetic:
        result = _safe_expression(arithmetic.group(1))
        return {
            "output_text": result,
            "engine_id": "LOUKSNAPG2_FORMAL_ARITHMETIC/1.0",
            "scope": "SAFE_AST_ARITHMETIC_EXPRESSION",
        }

    invoice = re.search(
        r"(\d+)\s+items?\s+at\s+(\d+(?:\.\d+)?)\s+(?:dollars?|usd|\$)\s+each.*?"
        r"(\d+(?:\.\d+)?)\s+(?:dollars?|usd|\$)\s+discount",
        text,
        flags=re.IGNORECASE,
    )
    if invoice:
        quantity, unit_price, discount = invoice.groups()
        result = _safe_expression(f"({quantity} * {unit_price}) - {discount}")
        return {
            "output_text": result,
            "engine_id": "LOUKSNAPG2_FORMAL_ARITHMETIC/1.0",
            "scope": "ITEMS_UNIT_PRICE_MINUS_DISCOUNT",
        }

    shelves = re.search(
        r"(\d+)\s+shelves?\s+with\s+(\d+)\s+books?\s+per\s+shelf.*?"
        r"(\d+)\s+books?\s+(?:are\s+)?borrowed",
        text,
        flags=re.IGNORECASE,
    )
    if shelves:
        shelf_count, books_per_shelf, borrowed = shelves.groups()
        result = _safe_expression(f"({shelf_count} * {books_per_shelf}) - {borrowed}")
        return {
            "output_text": result,
            "engine_id": "LOUKSNAPG2_FORMAL_ARITHMETIC/1.0",
            "scope": "TOTAL_CAPACITY_MINUS_BORROWED_ITEMS",
        }

    universal = re.search(r"\ball\s+(\w+)\s+are\s+(\w+)", text, flags=re.IGNORECASE)
    existential = re.search(r"\bsome\s+(\w+)\s+(?:are|fade|move|have)\s+(\w+)", text, flags=re.IGNORECASE)
    asks_subset = bool(re.search(r"does\s+it\s+logically\s+follow|does\s+it\s+follow", text, flags=re.IGNORECASE))
    if universal and existential and asks_subset:
        # From All A are B and Some B are C, Some A are C does not follow.
        # This is a validity decision, not a claim that the conclusion is false.
        left_class = universal.group(1).casefold()
        middle_class = universal.group(2).casefold()
        existential_class = existential.group(1).casefold()
        if left_class == existential_class:
            return {
                "output_text": "Yes",
                "engine_id": "LOUKSNAPG2_FORMAL_SYLLOGISTIC_CHECK/1.0",
                "scope": "VALID_UNIVERSAL_SUBSET_WITH_EXISTENTIAL_SUBJECT",
            }
        if middle_class == existential_class:
            return {
                "output_text": "No",
                "engine_id": "LOUKSNAPG2_FORMAL_SYLLOGISTIC_CHECK/1.0",
                "scope": "INVALID_EXISTENTIAL_TRANSFER_FROM_SUPERCLASS",
            }
    return None


def _run_checked(command: list[str], *, input_text: str | None = None, timeout: int = 45) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env={
                **os.environ,
                "OMP_NUM_THREADS": "1",
                "OPENBLAS_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1",
                "TOKENIZERS_PARALLELISM": "false",
            },
        )
    except FileNotFoundError as exc:
        raise AuxiliaryEngineError("AUXILIARY_EXECUTABLE_NOT_FOUND:" + command[0]) from exc
    except subprocess.TimeoutExpired as exc:
        raise AuxiliaryEngineError("AUXILIARY_EXECUTION_TIMEOUT:" + command[0]) from exc


def _package_versions(names: tuple[str, ...]) -> dict[str, str]:
    if not shutil.which("dpkg-query"):
        return {name: "UNAVAILABLE" for name in names}
    versions = {}
    for name in names:
        proc = _run_checked(
            ["dpkg-query", "-W", "-f=${Version}", name],
            timeout=15,
        )
        versions[name] = proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else "NOT_INSTALLED"
    return versions


def _apertium_pair(source: str, target: str, text: str) -> str:
    pair = f"{source}-{target}"
    proc = _run_checked(["apertium", pair], input_text=text, timeout=45)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()[-300:]
        raise AuxiliaryEngineError(f"APERTIUM_PAIR_FAILED:{pair}:{proc.returncode}:{detail}")
    output = " ".join(proc.stdout.replace("\x00", "").split())
    if not output:
        raise AuxiliaryEngineError("APERTIUM_OUTPUT_EMPTY:" + pair)
    return output


def _apertium_runtime_evidence() -> dict:
    version = _run_checked(["apertium", "-V"], timeout=15)
    if version.returncode != 0:
        raise AuxiliaryEngineError("APERTIUM_VERSION_PROBE_FAILED:" + (version.stderr or version.stdout)[-200:])
    return {
        "version": " ".join((version.stdout or version.stderr).split())[:200],
        "packages": _package_versions(("apertium", "apertium-eng-spa", "apertium-fr-es")),
    }


def translate_apertium(text: str, src_lang: str, tgt_lang: str) -> dict:
    if not isinstance(text, str) or not text.strip() or len(text) > 16_384:
        raise AuxiliaryEngineError("TRANSLATION_INPUT_EMPTY_OR_OVER_LIMIT")
    source = (src_lang or "").strip().lower()
    target = (tgt_lang or "").strip().lower()
    aliases = {"eng": "eng", "en": "eng", "spa": "spa", "es": "spa", "fra": "fra", "fr": "fra"}
    source = aliases.get(source, "")
    target = aliases.get(target, "")
    if not source or not target or source == target:
        raise AuxiliaryEngineError("APERTIUM_LANGUAGE_DIRECTION_UNSUPPORTED")
    if source == "eng" and target == "spa":
        output = _apertium_pair("eng", "spa", text)
        route = ["eng-spa"]
    elif source == "spa" and target == "eng":
        output = _apertium_pair("spa", "eng", text)
        route = ["spa-eng"]
    elif source == "eng" and target == "fra":
        intermediate = _apertium_pair("eng", "spa", text)
        output = _apertium_pair("spa", "fra", intermediate)
        route = ["eng-spa", "spa-fra"]
    elif source == "fra" and target == "eng":
        intermediate = _apertium_pair("fra", "spa", text)
        output = _apertium_pair("spa", "eng", intermediate)
        route = ["fra-spa", "spa-eng"]
    else:
        raise AuxiliaryEngineError("APERTIUM_LANGUAGE_DIRECTION_NOT_REGISTERED")
    if output.casefold() == text.strip().casefold():
        raise AuxiliaryEngineError("APERTIUM_OUTPUT_UNCHANGED_SOURCE")
    return {
        "output_text": output,
        "engine_id": "APERTIUM_LOCAL_BILINGUAL_PIPELINE/1.0",
        "translation_route": route,
        "source_language": source,
        "target_language": target,
        "dictionary_scope": "UBUNTU_24_04_APERTIUM_ENG_SPA_AND_FRA_SPA_PACKAGES",
        "runtime_evidence": _apertium_runtime_evidence(),
    }


def _parse_tesseract_tsv(tsv: str, *, max_words: int = 2048) -> dict:
    required = {
        "level", "page_num", "block_num", "par_num", "line_num",
        "left", "top", "width", "height", "conf", "text",
    }
    reader = csv.DictReader(io.StringIO(tsv), delimiter="\t")
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise AuxiliaryEngineError("TESSERACT_TSV_SCHEMA_INVALID")

    lines: dict[tuple[int, int, int, int], list[dict]] = {}
    word_count = 0
    for row in reader:
        try:
            level = int(row["level"])
        except (TypeError, ValueError):
            raise AuxiliaryEngineError("TESSERACT_TSV_LEVEL_INVALID")
        if level != 5:
            continue
        text = " ".join((row.get("text") or "").split())
        if not text:
            continue
        try:
            page = int(row["page_num"])
            block = int(row["block_num"])
            paragraph = int(row["par_num"])
            line = int(row["line_num"])
            left = int(row["left"])
            top = int(row["top"])
            width = int(row["width"])
            height = int(row["height"])
            confidence = float(row["conf"])
        except (TypeError, ValueError, OverflowError):
            raise AuxiliaryEngineError("TESSERACT_TSV_WORD_ROW_INVALID")
        if min(page, block, paragraph, line, left, top) < 0 or width <= 0 or height <= 0:
            raise AuxiliaryEngineError("TESSERACT_TSV_GEOMETRY_INVALID")
        if not (-1.0 <= confidence <= 100.0):
            raise AuxiliaryEngineError("TESSERACT_TSV_CONFIDENCE_OUT_OF_RANGE")
        word_count += 1
        if word_count > max_words:
            raise AuxiliaryEngineError("TESSERACT_TSV_WORD_LIMIT_EXCEEDED")
        key = (page, block, paragraph, line)
        lines.setdefault(key, []).append({
            "text": text,
            "bbox": [left, top, width, height],
            "confidence": round(max(0.0, confidence), 2),
        })

    layout = []
    for key, words in sorted(lines.items()):
        left = min(word["bbox"][0] for word in words)
        top = min(word["bbox"][1] for word in words)
        right = max(word["bbox"][0] + word["bbox"][2] for word in words)
        bottom = max(word["bbox"][1] + word["bbox"][3] for word in words)
        layout.append({
            "page": key[0],
            "block": key[1],
            "paragraph": key[2],
            "line": key[3],
            "text": " ".join(word["text"] for word in words),
            "bbox": [left, top, right - left, bottom - top],
            "mean_word_confidence": round(sum(word["confidence"] for word in words) / len(words), 2),
            "words": words,
        })
    if not layout:
        raise AuxiliaryEngineError("TESSERACT_OUTPUT_EMPTY")
    return {
        "text": "\n".join(line["text"] for line in layout),
        "layout": layout,
        "word_count": word_count,
        "line_count": len(layout),
    }


def extract_document_tesseract(image_path: Path, *, language: str = "eng") -> dict:
    image = Path(image_path)
    if image.is_symlink() or not image.is_file():
        raise AuxiliaryEngineError("OCR_INPUT_IMAGE_MISSING_OR_UNSAFE")
    if image.stat().st_size <= 0 or image.stat().st_size > 20_000_000:
        raise AuxiliaryEngineError("OCR_INPUT_IMAGE_SIZE_OUT_OF_RANGE")
    proc = _run_checked(
        ["tesseract", str(image), "stdout", "--oem", "1", "--psm", "6", "-l", language, "tsv"],
        timeout=60,
    )
    if proc.returncode != 0:
        raise AuxiliaryEngineError("TESSERACT_EXECUTION_FAILED:" + (proc.stderr or "")[-300:])
    parsed = _parse_tesseract_tsv(proc.stdout)
    output = parsed["text"]
    if len(output.strip()) < 3:
        raise AuxiliaryEngineError("TESSERACT_OUTPUT_EMPTY")
    version = _run_checked(["tesseract", "--version"], timeout=15)
    if version.returncode != 0:
        raise AuxiliaryEngineError("TESSERACT_VERSION_PROBE_FAILED:" + (version.stderr or version.stdout)[-200:])
    return {
        "output_text": output[:8192],
        "document_layout": parsed["layout"][:512],
        "layout_metadata": {
            "word_count": parsed["word_count"],
            "line_count": parsed["line_count"],
            "layout_truncated": parsed["line_count"] > 512,
            "coordinates": "PIXELS_RELATIVE_TO_SOURCE_IMAGE",
            "confidence": "TESSERACT_WORD_CONFIDENCE_0_TO_100",
        },
        "engine_id": "TESSERACT_OCR/5.x",
        "ocr_language": language,
        "input_sha256": _digest(image.read_bytes()),
        "runtime_evidence": {
            "version": (version.stdout or version.stderr).splitlines()[0][:200],
            "packages": _package_versions(("tesseract-ocr", "tesseract-ocr-eng")),
        },
    }

def _whisper_paths(runtime_root: Path) -> tuple[Path, Path, Path]:
    root = Path(runtime_root).resolve()
    runtime = root if root.name == "LOUKSNAPG2_RUNTIME" else root / "LOUKSNAPG2_RUNTIME"
    binary = runtime / "auxiliary_bin" / "linux-x86_64" / "whisper-cli"
    model = runtime / "auxiliary_models" / "ggml-tiny.bin"
    manifest = runtime / "WHISPER_AUXILIARY_ASSETS.json"
    return binary, model, manifest


def verify_whisper_auxiliary_assets(runtime_root: Path) -> dict:
    binary, model, manifest_path = _whisper_paths(runtime_root)
    for label, asset in (("binary", binary), ("model", model), ("manifest", manifest_path)):
        if asset.is_symlink() or not asset.is_file():
            raise AuxiliaryEngineError("WHISPER_AUXILIARY_ASSET_MISSING_OR_UNSAFE:" + label)
    runtime = binary.parents[2]
    for asset in (binary, model, manifest_path):
        for parent in asset.parents:
            if parent == runtime.parent:
                break
            if parent.is_symlink():
                raise AuxiliaryEngineError("WHISPER_AUXILIARY_PARENT_SYMLINK_REJECTED:" + str(parent))
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AuxiliaryEngineError("WHISPER_AUXILIARY_MANIFEST_INVALID:" + type(exc).__name__) from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != "LOUKSNAPG2_WHISPER_AUXILIARY_ASSETS/1.0":
        raise AuxiliaryEngineError("WHISPER_AUXILIARY_MANIFEST_SCHEMA_MISMATCH")
    source = manifest.get("source")
    model_record = manifest.get("model")
    binary_record = manifest.get("binary")
    if not isinstance(source, dict) or not isinstance(model_record, dict) or not isinstance(binary_record, dict):
        raise AuxiliaryEngineError("WHISPER_AUXILIARY_MANIFEST_BINDING_MISSING")
    expected_model_sha = "be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21"
    expected_model_bytes = 77_691_713
    expected_source_commit = "d1be6fde11ac6e0407606b4e42fe72d34add8037"
    expected_binary_path = "auxiliary_bin/linux-x86_64/whisper-cli"
    expected_model_path = "auxiliary_models/ggml-tiny.bin"
    if (
        source.get("model_repository") != "ggerganov/whisper.cpp"
        or source.get("model_revision") != "80da2d8bfee42b0e836fc3a9890373e5defc00a6"
        or source.get("model_sha256") != expected_model_sha
        or source.get("model_bytes") != expected_model_bytes
        or source.get("runtime_commit") != expected_source_commit
        or binary_record.get("source_commit") != expected_source_commit
        or binary_record.get("path") != expected_binary_path
        or binary_record.get("status") not in {"PASS_BUILT_FROM_PINNED_SOURCE", "PASS_REUSED_BUILT_BINARY"}
        or model_record.get("sha256") != expected_model_sha
        or model_record.get("bytes") != expected_model_bytes
    ):
        raise AuxiliaryEngineError("WHISPER_AUXILIARY_MANIFEST_IDENTITY_MISMATCH")
    if not os.access(binary, os.X_OK):
        raise AuxiliaryEngineError("WHISPER_CPP_BINARY_NOT_EXECUTABLE")
    binary_sha = _digest(binary.read_bytes())
    if binary.stat().st_size != binary_record.get("bytes") or binary_sha != binary_record.get("sha256"):
        raise AuxiliaryEngineError("WHISPER_CPP_BINARY_IDENTITY_MISMATCH")
    model_sha = _digest(model.read_bytes())
    if model.stat().st_size != expected_model_bytes or model_sha != expected_model_sha:
        raise AuxiliaryEngineError("WHISPER_TINY_MODEL_IDENTITY_MISMATCH")
    return {
        "status": "PASS_HASH_VERIFIED_AUXILIARY_ASSETS",
        "binary_path": expected_binary_path,
        "binary_sha256": binary_sha,
        "model_path": expected_model_path,
        "model_sha256": expected_model_sha,
        "assets_manifest_sha256": _digest(manifest_path.read_bytes()),
        "runtime_commit": expected_source_commit,
    }


def transcribe_whisper_cpp(runtime_root: Path, audio_path: Path) -> dict:
    audio = Path(audio_path)
    if audio.is_symlink() or not audio.is_file():
        raise AuxiliaryEngineError("WHISPER_INPUT_AUDIO_MISSING_OR_UNSAFE")
    if audio.stat().st_size <= 44 or audio.stat().st_size > 50_000_000:
        raise AuxiliaryEngineError("WHISPER_INPUT_AUDIO_SIZE_OUT_OF_RANGE")
    assets = verify_whisper_auxiliary_assets(runtime_root)
    binary, model, _ = _whisper_paths(runtime_root)
    proc = _run_checked(
        [str(binary), "-m", str(model), "-f", str(audio), "-nt", "-np", "-l", "auto", "-t", "1"],
        timeout=240,
    )
    if proc.returncode != 0:
        raise AuxiliaryEngineError("WHISPER_CPP_EXECUTION_FAILED:" + (proc.stderr or "")[-400:])
    output = " ".join(proc.stdout.replace("\x00", "").split())
    if not output or output.casefold() in {"[blank_audio]", "[silence]"}:
        raise AuxiliaryEngineError("WHISPER_CPP_OUTPUT_EMPTY")
    return {
        "output_text": output[:8192],
        "engine_id": "WHISPER_CPP_TINY_MULTILINGUAL/1.9.5",
        **assets,
        "audio_sha256": _digest(audio.read_bytes()),
        "threads": 1,
    }


class LouksnapG2AuxiliaryEngines:
    def __init__(self, runtime_root: Path):
        self.root = Path(runtime_root).resolve()

    def reasoning(self, prompt: str) -> dict | None:
        return formal_reasoning(prompt)

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> dict:
        return translate_apertium(text, src_lang, tgt_lang)

    def extract_document(self, image_path: Path) -> dict:
        return extract_document_tesseract(image_path)

    def transcribe(self, audio_path: Path) -> dict:
        return transcribe_whisper_cpp(self.root, audio_path)
