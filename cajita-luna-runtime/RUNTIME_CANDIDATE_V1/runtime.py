"""Small candidate runtime: integrity, bounded JSON and safetensors headers only."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import struct
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

REGISTRY_SHA256 = "e872101b9347356eb2e6574efbe7ae24986d0cef2b5e5c9288bb3e5d4f0ba22a"
MAX_JSON = 8 * 1024 * 1024
MAX_HEADER = 8 * 1024 * 1024
MAX_CONTROL = 8 * 1024 * 1024
OPERATIONS = ("integrity", "json_structure", "safetensors_header")
ZERO = "0" * 64


class Denied(ValueError):
    """Explicit fail-closed decision."""


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Denied("Duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(value):
        raise Denied("Non-finite JSON number")

    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise Denied("Non-finite JSON number")
        return result

    try:
        return json.loads(data, object_pairs_hook=pairs, parse_constant=reject_constant, parse_float=finite_float)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Denied("Invalid bounded JSON") from exc


def no_link(path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise Denied("Links and reparse points are forbidden")
    if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
        raise Denied("Hard-linked files are forbidden")
    return info


def bounded_path(root, relative, *, must_exist=True):
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative or "\x00" in relative:
        raise Denied("Invalid relative path")
    parts = PurePosixPath(relative).parts
    if PurePosixPath(relative).is_absolute() or any(x in (".", "..") or x.endswith((" ", ".")) for x in parts):
        raise Denied("Path escapes or aliases scope")
    if relative != "/".join(parts):
        raise Denied("Non-canonical relative path")
    # Check the entire real root chain, including a linked root or ancestor.
    for ancestor in reversed((root,) + tuple(root.parents)):
        no_link(ancestor)
    current = root
    for part in parts:
        current = current / part
        if current.exists() or current.is_symlink():
            no_link(current)
        elif must_exist:
            raise Denied("Required path absent in scope")
    if not current.resolve(strict=False).is_relative_to(root.resolve(strict=True)):
        raise Denied("Resolved path outside scope")
    return current


def state_valid(state):
    return isinstance(state, dict) and set(state) == {"active", "last_result"} and (state["active"] is None or isinstance(state["active"], dict))


class Runtime:
    def __init__(self, root, registry_path=None, expected_registry_sha=REGISTRY_SHA256):
        self.root = Path(root).absolute()
        no_link(self.root)
        registry_path = Path(registry_path) if registry_path else Path(__file__).with_name("registry.json")
        no_link(registry_path)
        if registry_path.stat().st_size > MAX_JSON:
            raise Denied("Registry exceeds bound")
        raw = registry_path.read_bytes()
        if digest(raw) != expected_registry_sha:
            raise Denied("Registry integrity mismatch")
        self.registry_sha = expected_registry_sha
        self.registry = strict_json(raw)
        if self.registry.get("schema_version") != 1:
            raise Denied("Unsupported registry schema")
        self.artifacts = {}
        seen_paths = set()
        for row in self.registry.get("artifacts", []):
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or row["id"] in self.artifacts:
                raise Denied("Invalid or duplicate artifact identifier")
            if type(row.get("size")) is not int or row["size"] < 0 or not re.fullmatch("[0-9a-f]{64}", row.get("sha256", "")):
                raise Denied("Invalid artifact integrity metadata")
            bounded_path(self.root, row.get("path"), must_exist=False)
            key = row["path"].casefold()
            if key in seen_paths or key.startswith("runtime_candidate_v1/state/"):
                raise Denied("Duplicate path or resource/control overlap")
            seen_paths.add(key)
            self.artifacts[row["id"]] = row
        self.capabilities = self.registry.get("capabilities", [])
        self.capability_index = {}
        required = {"id", "resource_set", "dependencies", "adapter_state", "operability_state", "activation_rule", "validation_rule", "block_reason", "trace_rule"}
        for cap in self.capabilities:
            if not isinstance(cap, dict) or not required.issubset(cap) or not isinstance(cap["id"], str) or cap["id"] in self.capability_index or not isinstance(cap["resource_set"], list) or not set(cap["resource_set"]).issubset(self.artifacts):
                raise Denied("Invalid capability references")
            if not isinstance(cap["dependencies"], dict) or "closure_state" not in cap["dependencies"]:
                raise Denied("Missing explicit capability dependency closure")
            self.capability_index[cap["id"]] = cap
        self.control_relative = "RUNTIME_CANDIDATE_V1/state"

    def list(self):
        return {"status": "RUNTIME_CANDIDATE", "operations": list(OPERATIONS), "artifacts": len(self.artifacts), "capabilities": self.capabilities, "accounting": self.registry.get("accounting", {}), "model_execution": "UNVERIFIED_AND_BLOCKED"}

    def plan(self, artifact_id, operation="auto"):
        if artifact_id not in self.artifacts:
            raise Denied("Unknown artifact identifier")
        row = self.artifacts[artifact_id]
        extension = PurePosixPath(row["path"]).suffix.lower()
        if operation == "auto":
            operation = "json_structure" if extension == ".json" and row["size"] <= MAX_JSON else "safetensors_header" if extension == ".safetensors" else "integrity"
        if operation not in OPERATIONS:
            raise Denied("Capability has no validated executable adapter")
        if operation == "json_structure" and (extension != ".json" or row["size"] > MAX_JSON):
            raise Denied("JSON operation incompatible or exceeds bound")
        if operation == "safetensors_header" and extension != ".safetensors":
            raise Denied("Header operation incompatible")
        plan = {"schema_version": 1, "registry_sha256": self.registry_sha, "artifact_id": artifact_id, "operation": operation, "source_sha256": row["sha256"], "source_bytes": row["size"], "selected_resources": [artifact_id], "dependency_policy": "STDLIB_ONLY_NO_MODEL_ADAPTER", "activation": "INACTIVE"}
        return {**plan, "plan_sha256": digest(canonical(plan))}

    def capability(self, capability_id):
        if capability_id not in self.capability_index:
            raise Denied("UNKNOWN_CAPABILITY")
        return self.capability_index[capability_id]

    def plan_capability(self, capability_id):
        cap = self.capability(capability_id)
        reasons = []
        if cap["adapter_state"] != "VALIDATED":
            reasons.append("MISSING_VALIDATED_ADAPTER")
        if cap["dependencies"]["closure_state"] != "VALIDATED":
            reasons.append("UNCLOSED_DEPENDENCY")
        # This candidate intentionally provides only resource operations.
        # A future flag alone cannot materialize a group execution adapter.
        if not reasons:
            reasons.append("GROUP_EXECUTION_ADAPTER_NOT_IMPLEMENTED")
        plan = {"capability_id": cap["id"], "resource_set": cap["resource_set"], "registry_sha256": self.registry_sha, "status": "BLOCKED", "activation": "INACTIVE", "block_reasons": reasons, "operability_state": "UNVERIFIED"}
        return {**plan, "plan_sha256": digest(canonical(plan))}

    def run_capability(self, capability_id):
        plan = self.plan_capability(capability_id)
        with self._lock():
            control = self._load()
            self._append(control, "BLOCK", plan)
        raise Denied("BLOCKED_CAPABILITY: " + ", ".join(plan["block_reasons"]))

    def _managed(self, name, must_exist=False):
        if not re.fullmatch(r"(?:control\.json|control\.json\.pending|lock|checkpoint-[0-9a-f]{64}\.json)", name):
            raise Denied("Invalid control filename")
        return bounded_path(self.root, self.control_relative + "/" + name, must_exist=must_exist)

    def _initialize(self):
        directory = bounded_path(self.root, self.control_relative, must_exist=False)
        directory.mkdir(parents=True, exist_ok=True)
        bounded_path(self.root, self.control_relative)

    @contextmanager
    def _lock(self):
        self._initialize()
        lock = self._managed("lock")
        try:
            with lock.open("xb") as stream:
                stream.write(b"single writer\n")
        except FileExistsError as exc:
            raise Denied("Concurrent or interrupted writer; explicit recovery required") from exc
        try:
            yield
        finally:
            lock.unlink()

    def _load(self):
        path = self._managed("control.json")
        if not path.exists():
            return {"schema_version": 1, "registry_sha256": self.registry_sha, "state": {"active": None, "last_result": None}, "events": []}
        if path.stat().st_size > MAX_CONTROL:
            raise Denied("Control journal exceeds bound")
        control = strict_json(path.read_bytes())
        if not isinstance(control, dict) or control.get("schema_version") != 1 or control.get("registry_sha256") != self.registry_sha or not state_valid(control.get("state")):
            raise Denied("Invalid control schema")
        previous = ZERO
        phase = "IDLE"
        current = {"active": None, "last_result": None}
        events = control.get("events")
        if not isinstance(events, list):
            raise Denied("Invalid event list")
        for seq, event in enumerate(events, 1):
            if not isinstance(event, dict) or set(event) != {"seq", "previous", "event", "details", "state", "sha256"} or not isinstance(event["details"], dict):
                raise Denied("Invalid event schema")
            payload = {k: v for k, v in event.items() if k != "sha256"}
            if event["seq"] != seq or event["previous"] != previous or digest(canonical(payload)) != event["sha256"] or not state_valid(event["state"]):
                raise Denied("Corrupt trace chain")
            before = current["active"] is not None
            after = event["state"]["active"] is not None
            allowed = {"PLAN": (False, False), "CHECKPOINT": (False, False), "ACTIVATE": (False, True), "VALIDATE": (True, True), "FAILURE": (True, True), "RELEASE": (True, False), "ROLLBACK": (False, False), "BLOCK": (False, False)}
            if event["event"] not in allowed or allowed[event["event"]] != (before, after):
                raise Denied("Invalid lifecycle transition")
            transitions = {"PLAN": ("IDLE", "PLANNED"), "CHECKPOINT": ("PLANNED", "CHECKPOINTED"), "ACTIVATE": ("CHECKPOINTED", "ACTIVE"), "VALIDATE": ("ACTIVE", "VALIDATED"), "FAILURE": ("ACTIVE", "FAILED"), "ROLLBACK": ("IDLE", "IDLE"), "BLOCK": ("IDLE", "IDLE")}
            if event["event"] == "RELEASE":
                expected = "PASS_LOCAL_OPERATION" if phase == "VALIDATED" else "FAIL_CLOSED" if phase == "FAILED" else None
                if expected is None or event["details"].get("outcome") != expected:
                    raise Denied("Release lacks matching validation or failure")
                phase = "IDLE"
            else:
                required, target = transitions[event["event"]]
                if phase != required:
                    raise Denied("Incomplete transaction sequence")
                phase = target
            current = event["state"]
            previous = event["sha256"]
        if current != control["state"]:
            raise Denied("State differs from replay")
        if phase != "IDLE":
            raise Denied("Interrupted transaction requires explicit recovery review")
        return control

    def _append(self, control, event, details, state=None):
        state = control["state"] if state is None else state
        record = {"seq": len(control["events"]) + 1, "previous": control["events"][-1]["sha256"] if control["events"] else ZERO, "event": event, "details": details, "state": state}
        record["sha256"] = digest(canonical(record))
        candidate = {**control, "state": state, "events": control["events"] + [record]}
        encoded = canonical(candidate) + b"\n"
        if len(encoded) > MAX_CONTROL:
            raise Denied("Control journal capacity reached; no silent truncation")
        pending = self._managed("control.json.pending")
        with pending.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(pending, self._managed("control.json"))
        control.clear()
        control.update(candidate)

    def _checkpoint(self, control):
        snapshot = {"registry_sha256": self.registry_sha, "state": control["state"], "seq": len(control["events"]), "head": control["events"][-1]["sha256"] if control["events"] else ZERO}
        raw = canonical(snapshot)
        name = "checkpoint-" + digest(raw) + ".json"
        path = self._managed(name)
        if path.exists():
            if path.read_bytes() != raw:
                raise Denied("Existing checkpoint mismatch")
        else:
            with path.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        self._append(control, "CHECKPOINT", {"checkpoint": name})
        return name

    def restore(self, checkpoint_name):
        with self._lock():
            control = self._load()
            if control["state"]["active"] is not None:
                raise Denied("Active or interrupted operation requires explicit recovery review")
            path = self._managed(checkpoint_name, must_exist=True)
            if path.stat().st_size > MAX_CONTROL:
                raise Denied("Checkpoint exceeds bound")
            raw = path.read_bytes()
            if path.name != "checkpoint-" + digest(raw) + ".json":
                raise Denied("Checkpoint integrity mismatch")
            snap = strict_json(raw)
            if not isinstance(snap, dict) or set(snap) != {"registry_sha256", "state", "seq", "head"} or not state_valid(snap.get("state")) or snap["state"]["active"] is not None or snap["registry_sha256"] != self.registry_sha:
                raise Denied("Checkpoint schema mismatch")
            seq = snap["seq"]
            if type(seq) is not int or not 0 <= seq <= len(control["events"]):
                raise Denied("Checkpoint lineage mismatch")
            head = control["events"][seq - 1]["sha256"] if seq else ZERO
            old_state = control["events"][seq - 1]["state"] if seq else {"active": None, "last_result": None}
            if head != snap["head"] or old_state != snap["state"]:
                raise Denied("Checkpoint is not an exact journal ancestor")
            self._append(control, "ROLLBACK", {"checkpoint": checkpoint_name}, snap["state"])
            return {"status": "RESTORED_CONTROL_STATE", "state": control["state"], "source_mutation": False}

    def _execute(self, plan):
        row = self.artifacts[plan["artifact_id"]]
        path = bounded_path(self.root, row["path"])
        before = no_link(path)
        if not stat.S_ISREG(before.st_mode) or before.st_size != row["size"]:
            raise Denied("Resource type or size mismatch")
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino) or opened.st_nlink != 1:
                raise Denied("Resource identity changed during open")
            hasher = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(chunk)
            if hasher.hexdigest() != row["sha256"]:
                raise Denied("Resource hash mismatch")
            stream.seek(0)
            result = {"artifact_id": row["id"], "operation": plan["operation"], "size": row["size"], "sha256": row["sha256"], "integrity": "PASS"}
            if plan["operation"] == "json_structure":
                value = strict_json(stream.read(MAX_JSON + 1))
                result["structure"] = {"root_type": type(value).__name__, "top_level_count": len(value) if isinstance(value, (dict, list)) else None}
            elif plan["operation"] == "safetensors_header":
                result["structure"] = self._header(stream, row["size"])
            after = os.fstat(stream.fileno())
            fields = ("st_size", "st_mtime_ns", "st_ctime_ns")
            if any(getattr(opened, x) != getattr(after, x) for x in fields):
                raise Denied("Resource changed during inspection")
        final_path_stat = no_link(bounded_path(self.root, row["path"]))
        if (final_path_stat.st_dev, final_path_stat.st_ino) != (after.st_dev, after.st_ino) or any(getattr(final_path_stat, x) != getattr(after, x) for x in fields):
            raise Denied("Resource path identity changed during inspection")
        result["validation_scope"] = "LOCAL_STRUCTURE_ONLY_NO_MODEL_EXECUTION"
        return result

    @staticmethod
    def _header(stream, total):
        prefix = stream.read(8)
        if len(prefix) != 8:
            raise Denied("Truncated safetensors prefix")
        length = struct.unpack("<Q", prefix)[0]
        if not 2 <= length <= MAX_HEADER or 8 + length > total:
            raise Denied("Invalid or excessive safetensors header length")
        header = strict_json(stream.read(length))
        if not isinstance(header, dict) or len(header) > 100000:
            raise Denied("Invalid safetensors header object")
        widths = {"BOOL": 1, "U8": 1, "I8": 1, "U16": 2, "I16": 2, "F16": 2, "BF16": 2, "U32": 4, "I32": 4, "F32": 4, "U64": 8, "I64": 8, "F64": 8, "F8_E4M3": 1, "F8_E5M2": 1}
        spans = []
        for name, tensor in header.items():
            if name == "__metadata__":
                if not isinstance(tensor, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in tensor.items()):
                    raise Denied("Invalid safetensors metadata")
                continue
            if not isinstance(tensor, dict) or set(tensor) != {"dtype", "shape", "data_offsets"} or tensor["dtype"] not in widths:
                raise Denied("Unsupported or invalid tensor descriptor")
            shape, offsets = tensor["shape"], tensor["data_offsets"]
            if not isinstance(shape, list) or len(shape) > 64 or not all(type(x) is int and 0 <= x <= total for x in shape):
                raise Denied("Invalid tensor dimensions")
            if not isinstance(offsets, list) or len(offsets) != 2 or not all(type(x) is int and x >= 0 for x in offsets):
                raise Denied("Invalid tensor offsets")
            start, end = offsets
            if start > end or end > total - 8 - length or end - start != math.prod(shape) * widths[tensor["dtype"]]:
                raise Denied("Tensor byte geometry mismatch")
            spans.append((start, end))
        position = 0
        for start, end in sorted(spans):
            if start != position:
                raise Denied("Overlapping or discontinuous tensor payload")
            position = end
        if position != total - 8 - length:
            raise Denied("Unindexed tensor payload")
        return {"tensor_count": len(spans), "header_bytes": length, "payload_bytes": position, "weights_loaded": False}

    def run(self, artifact_id, operation="auto"):
        plan = self.plan(artifact_id, operation)
        with self._lock():
            control = self._load()
            if control["state"]["active"] is not None:
                raise Denied("Previous operation remains active; fail closed")
            previous_result = control["state"]["last_result"]
            self._append(control, "PLAN", plan)
            checkpoint = self._checkpoint(control)
            self._append(control, "ACTIVATE", {"plan_sha256": plan["plan_sha256"]}, {"active": plan, "last_result": previous_result})
            try:
                result = self._execute(plan)
                self._append(control, "VALIDATE", {"result_sha256": digest(canonical(result)), "scope": result["validation_scope"]})
            except Exception as exc:
                self._append(control, "FAILURE", {"error_type": type(exc).__name__, "message": str(exc)})
                self._append(control, "RELEASE", {"outcome": "FAIL_CLOSED", "checkpoint": checkpoint}, {"active": None, "last_result": previous_result})
                raise Denied("Operation rejected; capability released; " + str(exc)) from exc
            self._append(control, "RELEASE", {"outcome": "PASS_LOCAL_OPERATION", "checkpoint": checkpoint}, {"active": None, "last_result": result})
            self._load()  # Replay validates persisted state, not only in-memory data.
            return {"status": "PASS_LOCAL_OPERATION", "result": result, "checkpoint": checkpoint, "trace_head": control["events"][-1]["sha256"], "model_operability": "UNVERIFIED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list", "plan", "run", "capability", "plan-capability", "run-capability", "restore", "audit-state"))
    parser.add_argument("identifier", nargs="?")
    parser.add_argument("--operation", default="auto")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    try:
        runtime = Runtime(args.root)
        if args.command == "list":
            result = runtime.list()
        elif args.command == "audit-state":
            control = runtime._load()
            result = {"state": control["state"], "event_count": len(control["events"]), "trace_integrity": "PASS"}
        elif args.command == "restore":
            result = runtime.restore(args.identifier or "")
        elif args.command in ("capability", "plan-capability", "run-capability"):
            result = getattr(runtime, args.command.replace("-", "_"))(args.identifier)
        else:
            result = getattr(runtime, args.command)(args.identifier, args.operation)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    except (Denied, OSError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": str(exc)}, ensure_ascii=False))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
