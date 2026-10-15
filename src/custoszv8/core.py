"""CUSTOSZ V8: governed integration primitives (stdlib only)."""
from __future__ import annotations
import ast
import hashlib
import importlib.resources
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

VERSION = "8.0.0-candidate"
AUTHORITY = "Louksna.md"
DOCTRINE = "EXTEND_DO_NOT_REPLACE"
FAILURE_POLICY = "FAIL_CLOSED"
CANONICAL_GATES = tuple(f"G{i:02d}" for i in range(1, 25))
LOCAL_PUAC_CONTROLS = tuple(f"PUAC.C{i}" for i in range(25, 33))
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_PATTERNS = [
    re.compile(r"(?<!\w)/[A-Za-z0-9_.\-/]+"),
    re.compile(r"\b[A-Fa-f0-9]{40,64}\b"),
    re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b"),
    re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\.(?:pyz|wasm|py|json|md|yml|yaml)\b"),
]
_BACKTICK = chr(96)

class V8Error(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code, self.message = code, message

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None

def load_resource_json(relative: str) -> dict[str, Any]:
    try:
        raw = importlib.resources.files("custoszv8").joinpath("data", relative).read_bytes()
        obj = json.loads(raw.decode("utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("root must be object")
        return obj
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise V8Error("V8E001", f"cannot load resource {relative}: {exc}") from exc

def validate_manifest(manifest: dict[str, Any], require_final_identity: bool = False) -> list[str]:
    required = {"schema_version", "artifact_id", "artifact_version", "artifact_status",
                "canonical_authority_ref", "components", "capability_ownership",
                "gates", "certification", "limitations"}
    issues = [f"missing required field: {key}" for key in sorted(required - manifest.keys())]
    if manifest.get("schema_version") != "1.0.0":
        issues.append("unsupported schema_version")
    components = manifest.get("components")
    if not isinstance(components, dict):
        issues.append("components must be an object")
    else:
        for name, item in components.items():
            if not isinstance(item, dict):
                issues.append(f"component {name} must be an object")
                continue
            digest = item.get("sha256")
            if digest is not None and not is_sha256(digest):
                issues.append(f"component {name} has malformed SHA-256")
            if require_final_identity and not is_sha256(digest):
                issues.append(f"component {name} lacks a final SHA-256")
    cert = manifest.get("certification", {})
    if cert.get("g23") not in {"NOT_GRANTED", "PASS", "FAIL", "HOLD"}:
        issues.append("invalid G23 state")
    if cert.get("g24") not in {"NOT_GRANTED", "APPROVED", "DENIED", "HOLD"}:
        issues.append("invalid G24 state")
    if require_final_identity and cert.get("g23") != "PASS":
        issues.append("G23 is not PASS")
    if require_final_identity and cert.get("g24") != "APPROVED":
        issues.append("G24 is not APPROVED")
    return issues

class CapabilityRegistry:
    """No implicit owner conflict resolution."""
    def __init__(self, records: Iterable[dict[str, Any]]):
        self.records = list(records)

    def validate(self) -> list[str]:
        issues, owners = [], {}
        for i, record in enumerate(self.records):
            cap, owner = record.get("capability_id"), record.get("owner_component")
            if not isinstance(cap, str) or not cap.strip():
                issues.append(f"record {i}: missing capability_id")
                continue
            if not isinstance(owner, str) or not owner.strip():
                issues.append(f"{cap}: missing owner_component")
            if cap in owners and owners[cap] != owner:
                issues.append(f"{cap}: conflicting owners {owners[cap]} and {owner}")
            owners.setdefault(cap, str(owner))
            if record.get("overlaps") and not record.get("overlap_review_ref"):
                issues.append(f"{cap}: overlap lacks review evidence")
        return issues

    def resolve(self, capability_id: str) -> dict[str, Any]:
        matches = [x for x in self.records if x.get("capability_id") == capability_id]
        if len(matches) != 1:
            raise V8Error("V8E006", f"capability must have exactly one record: {capability_id}")
        item = matches[0]
        if item.get("status") not in {"VERIFIED", "ENABLED"} or not item.get("owner_component"):
            raise V8Error("V8E006", f"capability not enabled: {capability_id}")
        issues = self.validate()
        if issues:
            raise V8Error("V8E007", "; ".join(issues))
        return item

ALLOWED_TRANSITIONS = {
    "RECEIVED": {"PREFLIGHT"},
    "PREFLIGHT": {"READY", "BLOCKED", "HOLD", "FAILED_WITH_EVIDENCE"},
    "READY": {"RUNNING", "BLOCKED", "HOLD"},
    "RUNNING": {"WAITING_FOR_DEPENDENCY", "CHECKPOINTED", "VALIDATING", "RETRY_WAIT",
                "RECOVERING", "COMPLETED", "FAILED_WITH_EVIDENCE", "HOLD", "QUARANTINED"},
    "WAITING_FOR_DEPENDENCY": {"RUNNING", "RETRY_WAIT", "RECOVERING", "HOLD", "FAILED_WITH_EVIDENCE"},
    "RETRY_WAIT": {"RUNNING", "RECOVERING", "HOLD", "FAILED_WITH_EVIDENCE"},
    "CHECKPOINTED": {"RUNNING", "VALIDATING", "RECOVERING", "HOLD"},
    "VALIDATING": {"COMPLETED", "RUNNING", "RECOVERING", "FAILED_WITH_EVIDENCE", "HOLD"},
    "RECOVERING": {"CHECKPOINTED", "RUNNING", "VALIDATING", "FAILED_WITH_EVIDENCE", "QUARANTINED", "HOLD"},
    "BLOCKED": {"PREFLIGHT", "HOLD", "CANCELLED_AUTHORIZED"},
    "HOLD": {"PREFLIGHT", "CANCELLED_AUTHORIZED"},
    "QUARANTINED": {"HOLD", "RECOVERING"},
    "COMPLETED": set(), "FAILED_WITH_EVIDENCE": set(), "CANCELLED_AUTHORIZED": set(),
}
TERMINAL_STATES = {"COMPLETED", "FAILED_WITH_EVIDENCE", "CANCELLED_AUTHORIZED"}

class MissionStateMachine:
    def transition(self, current: str, target: str) -> str:
        if current not in ALLOWED_TRANSITIONS or target not in ALLOWED_TRANSITIONS[current]:
            raise V8Error("V8E030", f"forbidden transition {current} -> {target}")
        return target

    @staticmethod
    def is_terminal(state: str) -> bool:
        return state in TERMINAL_STATES

class EvidenceJournal:
    """Append-only JSONL hash-chain journal; rejects corrupt prior history."""
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def record_hash(record: dict[str, Any]) -> str:
        clean = {k: v for k, v in record.items() if k != "current_event_hash"}
        return sha256_bytes(canonical_json(clean).encode("utf-8"))

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        raw = self.path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise V8Error("V8E019", "journal ends with incomplete record")
        out = []
        for n, line in enumerate(raw.splitlines(), 1):
            try:
                obj = json.loads(line.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise V8Error("V8E019", f"invalid journal record {n}") from exc
            if not isinstance(obj, dict):
                raise V8Error("V8E019", f"journal record {n} is not an object")
            out.append(obj)
        return out

    def verify(self) -> dict[str, Any]:
        rows, previous = self.records(), "GENESIS"
        for seq, row in enumerate(rows, 1):
            if row.get("sequence_number") != seq or row.get("previous_event_hash") != previous:
                raise V8Error("V8E019", f"sequence/parent mismatch at record {seq}")
            digest = row.get("current_event_hash")
            if not is_sha256(digest) or digest != self.record_hash(row):
                raise V8Error("V8E019", f"hash mismatch at record {seq}")
            previous = digest
        return {"status": "PASS", "records": len(rows), "head": previous}

    def append(self, event_type: str, payload: dict[str, Any], actor_id: str = "local-user",
               mission_id: str | None = None) -> dict[str, Any]:
        if not event_type or not isinstance(payload, dict):
            raise V8Error("V8E019", "event_type and dict payload are required")
        state = self.verify()
        row = {
            "event_id": f"EVT-{state['records'] + 1:08d}-{sha256_bytes(os.urandom(16))[:8]}",
            "sequence_number": state["records"] + 1,
            "event_type": event_type, "actor_id": actor_id, "mission_id": mission_id,
            "event_time_utc": utc_now(), "observed_at_utc": utc_now(), "recorded_at_utc": utc_now(),
            "payload": payload, "previous_event_hash": state["head"],
        }
        row["current_event_hash"] = self.record_hash(row)
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        fd = os.open(self.path, flags, 0o600)
        with os.fdopen(fd, "ab") as stream:
            stream.write((canonical_json(row) + "\n").encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        return row

class TranslationEngine:
    """Conservative phrase-level translator; unknown text is never guessed as a full translation."""
    PHRASES = (
        ("sin bloquear las demás", "without blocking independent missions"),
        ("en el plazo establecido", "within the configured deadline"),
        ("intenta recuperarlo una sola vez", "attempt recovery exactly once"),
        ("guarda la evidencia", "persist the evidence"),
        ("si el runtime no responde", "if the runtime fails to respond"),
        ("si falla", "if recovery fails"),
        ("detén esa misión", "stop the affected mission"),
        ("detén la misión afectada", "stop the affected mission"),
        ("no ejecutes", "do not execute"),
        ("no modificar", "do not modify"),
        ("sin autorización", "without authorization"),
        ("fallo cerrado", "fail-closed"),
        ("reintento acotado", "bounded retry"),
        ("evidencia trazable", "traceable evidence"),
        (" y,", " and,"),
        ("sin regresión", "without regression"),
        ("conserva los identificadores", "preserve the identifiers"),
        ("no sobrescribas", "do not overwrite"),
        ("no ejecutes código", "do not execute code"),
    )

    def _protect(self, text: str) -> tuple[str, dict[str, str]]:
        pattern = re.compile(
            re.escape(_BACKTICK) + r"[^" + re.escape(_BACKTICK) + r"\n]+" + re.escape(_BACKTICK)
            + r"|\b[A-Fa-f0-9]{40,64}\b|\b[A-Z][A-Z0-9_]{2,}\b"
            + r"|\b[a-zA-Z_][a-zA-Z0-9_]*\.(?:pyz|wasm|py|json|md|yml|yaml)\b"
        )
        held = {}
        def sub(match: re.Match[str]) -> str:
            key = f"V8PROTECTEDTOKEN{len(held):04d}X"
            held[key] = match.group(0)
            return key
        return pattern.sub(sub, text), held

    def translate(self, text: str, source: str, target: str) -> dict[str, Any]:
        if not isinstance(text, str) or not text.strip():
            raise V8Error("V8E017", "input text must be non-empty")
        source, target = source.lower(), target.lower()
        if (source, target) not in {("es", "en"), ("en", "es")}:
            raise V8Error("V8E017", "supported deterministic profile is es<->en")
        protected_source = self._protected_tokens(text)
        working, held = self._protect(text)
        pairs = sorted(self.PHRASES, key=lambda p: len(p[0]), reverse=True)
        if source == "en":
            pairs = [(b, a) for a, b in pairs]
        hits = 0
        for old, new in pairs:
            working, count = re.subn(re.escape(old), new, working, flags=re.IGNORECASE)
            hits += count
        for key, value in held.items():
            working = working.replace(key, value)
        covered = self._covered(text, source)
        status = "PASS" if source == target or (hits and covered) else ("PARTIAL" if hits else "UNKNOWN")
        protected_output = self._protected_tokens(working)
        preserved = protected_source == protected_output
        if not preserved:
            status = "FAIL"
        return {
            "source_language": source, "target_language": target, "source_text": text,
            "translation": working if hits or source == target else "",
            "phrase_rules_applied": hits, "protected_tokens_preserved": preserved,
            "protected_tokens_source": protected_source, "protected_tokens_output": protected_output,
            "validation_state": status, "execution_authorized": False, "translator_version": VERSION,
        }

    @staticmethod
    def _protected_tokens(text: str) -> list[str]:
        result = []
        pattern = re.compile(
            re.escape(_BACKTICK) + r"[^" + re.escape(_BACKTICK) + r"\n]+" + re.escape(_BACKTICK)
            + r"|\b[A-Fa-f0-9]{40,64}\b|\b[A-Z][A-Z0-9_]{2,}\b"
            + r"|\b[a-zA-Z_][a-zA-Z0-9_]*\.(?:pyz|wasm|py|json|md|yml|yaml)\b"
        )
        return [m.group(0) for m in pattern.finditer(text)]

    def _covered(self, text: str, source: str) -> bool:
        plain, _held = self._protect(text)
        plain = re.sub(r"V8PROTECTEDTOKEN[0-9]{4}X", "", plain).lower()
        phrases = [a if source == "es" else b for a, b in self.PHRASES]
        for phrase in sorted(phrases, key=len, reverse=True):
            plain = re.sub(re.escape(phrase), "", plain, flags=re.IGNORECASE)
        plain = re.sub(r"[\s,.;:!?¡¿()\-]+", "", plain)
        return not plain

    @staticmethod
    def code_to_english(source: str, filename: str = "<input>") -> dict[str, Any]:
        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError as exc:
            raise V8Error("V8E017", f"Python parse error at line {exc.lineno}: {exc.msg}") from exc
        imports, funcs, classes, effects = [], [], [], []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(f"{node.module or ''}:{','.join(a.name for a in node.names)}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs.append({"name": node.name, "line": node.lineno, "async": isinstance(node, ast.AsyncFunctionDef)})
            elif isinstance(node, ast.ClassDef):
                classes.append({"name": node.name, "line": node.lineno})
            elif isinstance(node, ast.Call):
                name = TranslationEngine._call_name(node.func)
                if name and any(term in name.lower() for term in
                    ("subprocess", "remove", "unlink", "rmtree", "replace", "write_text", "write_bytes", "system", "popen", "urlopen", "request")):
                    effects.append({"call": name, "line": getattr(node, "lineno", None)})
        return {
            "filename": filename,
            "summary": f"Parsed Python source without execution: {len(funcs)} function(s), {len(classes)} class(es), {len(imports)} import(s), {len(effects)} potentially effectful call(s).",
            "imports": sorted(set(imports)), "functions": sorted(funcs, key=lambda x: (x["line"], x["name"])),
            "classes": sorted(classes, key=lambda x: (x["line"], x["name"])),
            "potentially_effectful_calls": sorted(effects, key=lambda x: (x.get("line") or 0, x["call"])),
            "source_executed": False,
        }

    @staticmethod
    def _call_name(node: ast.AST) -> str | None:
        names, cur = [], node
        while isinstance(cur, ast.Attribute):
            names.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            names.append(cur.id)
            return ".".join(reversed(names))
        return None

def _read_leb(data: bytes, offset: int) -> tuple[int, int]:
    value, shift = 0, 0
    while True:
        if offset >= len(data) or shift > 35:
            raise V8Error("V8E014", "malformed WASM LEB128 integer")
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7f) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7

def _read_name(data: bytes, offset: int) -> tuple[str, int]:
    size, offset = _read_leb(data, offset)
    end = offset + size
    if end > len(data):
        raise V8Error("V8E014", "WASM name exceeds section")
    try:
        return data[offset:end].decode("utf-8"), end
    except UnicodeDecodeError as exc:
        raise V8Error("V8E014", "invalid UTF-8 WASM name") from exc

def inspect_wasm(path: str | Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    if len(raw) < 8 or raw[:4] != b"\x00asm" or raw[4:8] != b"\x01\x00\x00\x00":
        raise V8Error("V8E014", "invalid/unsupported WebAssembly header")
    imports, exports, offset = [], [], 8
    while offset < len(raw):
        section_id = raw[offset]
        offset += 1
        size, offset = _read_leb(raw, offset)
        end = offset + size
        if end > len(raw):
            raise V8Error("V8E014", "WASM section exceeds module size")
        section, cur = raw[offset:end], 0
        if section_id in (2, 7):
            count, cur = _read_leb(section, cur)
            for _ in range(count):
                name = None
                if section_id == 2:
                    module, cur = _read_name(section, cur)
                    name, cur = _read_name(section, cur)
                else:
                    name, cur = _read_name(section, cur)
                if cur >= len(section):
                    raise V8Error("V8E014", "truncated WASM import/export")
                kind = section[cur]
                cur += 1
                record = {"name": name, "kind_id": kind}
                if section_id == 2:
                    record["module"] = module
                    if kind == 0:
                        record["type_index"], cur = _read_leb(section, cur)
                        record["kind"] = "FUNCTION"
                    elif kind == 1:
                        if cur >= len(section): raise V8Error("V8E014", "truncated table type")
                        record["kind"] = "TABLE"; cur += 1
                        flags, cur = _read_leb(section, cur)
                        _, cur = _read_leb(section, cur)
                        if flags & 1: _, cur = _read_leb(section, cur)
                    elif kind == 2:
                        record["kind"] = "MEMORY"
                        flags, cur = _read_leb(section, cur); _, cur = _read_leb(section, cur)
                        if flags & 1: _, cur = _read_leb(section, cur)
                    elif kind == 3:
                        record["kind"] = "GLOBAL"
                        if cur + 2 > len(section): raise V8Error("V8E014", "truncated global type")
                        record["value_type"], record["mutable"] = section[cur], section[cur + 1]; cur += 2
                    elif kind == 4:
                        record["kind"] = "TAG"
                        if cur >= len(section): raise V8Error("V8E014", "truncated tag type")
                        record["attribute"] = section[cur]; cur += 1
                        record["type_index"], cur = _read_leb(section, cur)
                    else:
                        raise V8Error("V8E014", f"unknown WASM import kind {kind}")
                    imports.append(record)
                else:
                    index, cur = _read_leb(section, cur)
                    exports.append({"name": name, "kind": {0:"FUNCTION",1:"TABLE",2:"MEMORY",3:"GLOBAL",4:"TAG"}.get(kind,"UNKNOWN"),
                                    "kind_id": kind, "index": index, "signature_verified": False})
        offset = end
    return {"path": str(path), "sha256": sha256_bytes(raw), "size_bytes": len(raw),
            "format": "WASM", "version": 1, "imports": imports, "exports": exports,
            "function_signatures_verified": False, "status": "STATIC_METADATA_INSPECTED_ABI_INCOMPLETE",
            "execution_authorized": False}

def inspect_archive(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    digest = sha256_file(path)
    if not zipfile.is_zipfile(path):
        return {"path": str(path), "sha256": digest, "size_bytes": path.stat().st_size,
                "format": "NON_ZIP", "status": "NOT_A_ZIPAPP"}
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [i.filename for i in infos]
            unsafe = [n for n in names if n.startswith("/") or ".." in Path(n).parts]
            if unsafe:
                raise V8Error("V8E002", f"unsafe archive paths: {unsafe}")
            return {"path": str(path), "sha256": digest, "size_bytes": path.stat().st_size,
                    "format": "ZIPAPP_CANDIDATE" if "__main__.py" in names else "ZIP_ARCHIVE",
                    "has_main": "__main__.py" in names, "entries": names, "entry_count": len(names),
                    "uncompressed_bytes": sum(i.file_size for i in infos),
                    "status": "PASS_STATIC_ARCHIVE_INSPECTION", "execution_authorized": False}
    except zipfile.BadZipFile as exc:
        raise V8Error("V8E002", f"invalid ZIP archive: {exc}") from exc

def verify_component(path: str | Path, expected_sha256: str | None = None) -> dict[str, Any]:
    path = Path(path)
    observed = sha256_file(path)
    if expected_sha256 is not None and not is_sha256(expected_sha256):
        raise V8Error("V8E002", "expected SHA-256 malformed")
    if expected_sha256 is not None and observed != expected_sha256:
        return {"path": str(path), "expected_sha256": expected_sha256, "observed_sha256": observed,
                "status": "CONFLICT", "execution_authorized": False}
    result = inspect_archive(path) if path.suffix.lower() in {".pyz", ".zip"} else (
        inspect_wasm(path) if path.suffix.lower() == ".wasm" else
        {"path": str(path), "sha256": observed, "size_bytes": path.stat().st_size,
         "format": path.suffix.lower(), "status": "HASH_VERIFIED", "execution_authorized": False})
    if str(result.get("status", "")).startswith("PASS"):
        result["status"] = "PASS_IDENTITY_AND_STATIC_INSPECTION"
    return result

def run_native_readonly(component_path: str | Path, command: str, *, expected_sha256: str,
                        authorization_ref: str | None, timeout_seconds: float = 10.0) -> dict[str, Any]:
    if os.environ.get("CUSTOSZV8_ALLOW_NATIVE_EXECUTION") != "1" or not authorization_ref:
        raise V8Error("V8E008", "native execution requires explicit opt-in and authorization_ref")
    if command not in {"v07-status", "v07-selftest"}:
        raise V8Error("V8E005", "command outside read-only native allowlist")
    path = Path(component_path).resolve(strict=True)
    info = verify_component(path, expected_sha256)
    if info.get("status") != "PASS_IDENTITY_AND_STATIC_INSPECTION" or not info.get("has_main"):
        raise V8Error("V8E003", "component identity/static inspection failed")
    try:
        proc = subprocess.run([sys.executable, "-I", str(path), command], stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=max(.1, min(float(timeout_seconds), 30.0)),
            check=False, env={"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8",
                              "PYTHONDONTWRITEBYTECODE": "1"})
    except subprocess.TimeoutExpired as exc:
        return {"status": "FAIL", "error_code": "V8E010", "timed_out": True,
                "stdout": exc.stdout or "", "stderr": exc.stderr or "", "execution_authorized": True}
    return {"status": "PASS" if proc.returncode == 0 else "FAIL", "exit_code": proc.returncode,
            "stdout": proc.stdout[-20000:], "stderr": proc.stderr[-20000:], "component_sha256": info["sha256"],
            "command": command, "authorization_ref": authorization_ref, "execution_authorized": True}

class GitHubBridge:
    API = "https://api.github.com"
    def __init__(self, token: str | None = None, timeout_seconds: float = 15.0):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.timeout_seconds = max(1.0, min(float(timeout_seconds), 60.0))

    def _request(self, method: str, route: str, payload: dict[str, Any] | None = None,
                 authorization_ref: str | None = None) -> dict[str, Any]:
        if not route.startswith("/") or ".." in route.split("/") or method not in {"GET", "POST"}:
            raise V8Error("V8E021", "invalid GitHub API request")
        if method != "GET" and (not self.token or not authorization_ref):
            raise V8Error("V8E008", "GitHub write requires GITHUB_TOKEN and authorization_ref")
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "CUSTOSZV8/8.0.0-candidate"}
        body = None if payload is None else canonical_json(payload).encode()
        if body is not None: headers["Content-Type"] = "application/json"
        if self.token: headers["Authorization"] = f"Bearer {self.token}"
        try:
            req = urllib.request.Request(self.API + route, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read(2 * 1024 * 1024 + 1)
                if len(raw) > 2 * 1024 * 1024:
                    raise V8Error("V8E021", "GitHub response exceeds 2 MiB limit")
                if not raw: return {"status_code": response.status, "body": None}
                try: parsed = json.loads(raw.decode("utf-8"))
                except (UnicodeError, json.JSONDecodeError) as exc: raise V8Error("V8E021", "invalid GitHub JSON response") from exc
                return {"status_code": response.status, "body": parsed}
        except urllib.error.HTTPError as exc:
            raise V8Error("V8E021", f"GitHub HTTP {exc.code}: {exc.read(4000).decode('utf-8','replace')}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise V8Error("V8E021", f"GitHub transport failed: {exc}") from exc

    @staticmethod
    def _validate_repo(owner: str, repo: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", repo):
            raise V8Error("V8E021", "invalid owner/repository")

    def inspect_repository(self, owner: str, repo: str) -> dict[str, Any]:
        self._validate_repo(owner, repo)
        return self._request("GET", f"/repos/{owner}/{repo}")["body"]

    def inspect_branch(self, owner: str, repo: str, branch: str) -> dict[str, Any]:
        self._validate_repo(owner, repo)
        return self._request("GET", f"/repos/{owner}/{repo}/branches/{urllib.parse.quote(branch, safe='')}")["body"]

    def workflow_runs(self, owner: str, repo: str, branch: str | None = None) -> dict[str, Any]:
        self._validate_repo(owner, repo)
        query = "" if not branch else "?branch=" + urllib.parse.quote(branch, safe="")
        return self._request("GET", f"/repos/{owner}/{repo}/actions/runs{query}")["body"]

    def dispatch_workflow(self, owner: str, repo: str, workflow_id: str, ref: str,
                          inputs: dict[str, str], authorization_ref: str) -> dict[str, Any]:
        self._validate_repo(owner, repo)
        if not authorization_ref or not re.fullmatch(r"[A-Za-z0-9_.-]+", workflow_id):
            raise V8Error("V8E008", "workflow dispatch requires authorization and valid workflow id")
        return self._request("POST", f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches",
                             {"ref": ref, "inputs": inputs}, authorization_ref)

def selftest() -> dict[str, Any]:
    results = []
    def run(name: str, func) -> None:
        try: func(); results.append({"name": name, "status": "PASS"})
        except Exception as exc: results.append({"name": name, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    def test_sha():
        assert sha256_bytes(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    def test_manifest():
        m = {"schema_version":"1.0.0","artifact_id":"CUSTOSZV8","artifact_version":VERSION,
             "artifact_status":"CANDIDATE","canonical_authority_ref":"Louksna.md","components":{},
             "capability_ownership":[],"gates":[],"certification":{"g23":"NOT_GRANTED","g24":"NOT_GRANTED"},"limitations":[]}
        assert validate_manifest(m) == []
    def test_transition():
        sm = MissionStateMachine()
        assert sm.transition("RECEIVED", "PREFLIGHT") == "PREFLIGHT"
        try: sm.transition("RECEIVED", "RUNNING")
        except V8Error: return
        raise AssertionError("forbidden transition accepted")
    def test_translation():
        text = ("Si el runtime no responde en el plazo establecido, guarda la evidencia, "
                "intenta recuperarlo una sola vez y, si falla, detén esa misión sin bloquear las demás.")
        r = TranslationEngine().translate(text, "es", "en")
        assert r["validation_state"] == "PASS", r
        assert "attempt recovery exactly once" in r["translation"]
        assert r["execution_authorized"] is False
    def test_code_parse():
        r = TranslationEngine.code_to_english("def f(x):\n    return x + 1\n")
        assert r["functions"][0]["name"] == "f" and r["source_executed"] is False
    def test_wasm():
        data = b"\x00asm\x01\x00\x00\x00\x07\x05\x01\x01f\x00\x00"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "fixture.wasm"; p.write_bytes(data)
            assert inspect_wasm(p)["exports"][0]["name"] == "f"
    def test_journal():
        with tempfile.TemporaryDirectory() as td:
            j = EvidenceJournal(Path(td) / "events.jsonl")
            j.append("TEST", {"x":1}); j.append("TEST", {"x":2})
            assert j.verify()["records"] == 2
    def test_ownership():
        r = CapabilityRegistry([{"capability_id":"A","owner_component":"ONE","status":"VERIFIED"}])
        assert r.resolve("A")["owner_component"] == "ONE"
    for name, fn in [
        ("sha256", test_sha), ("manifest_validation", test_manifest), ("mission_state_machine", test_transition),
        ("spanish_english_translation", test_translation), ("code_to_english_static_analysis", test_code_parse),
        ("wasm_export_inspection", test_wasm), ("append_only_evidence_journal", test_journal),
        ("capability_single_owner", test_ownership)
    ]: run(name, fn)
    return {"artifact":"CUSTOSZV8","version":VERSION,"timestamp_utc":utc_now(),
            "status":"PASS" if all(x["status"]=="PASS" for x in results) else "FAIL",
            "checks_passed":sum(x["status"]=="PASS" for x in results),"checks_total":len(results),
            "checks":results,"g23":"NOT_GRANTED","g24":"NOT_GRANTED","certification":"NOT_GRANTED",
            "native_integration":"NOT_CLAIMED_BY_SELFTEST"}
