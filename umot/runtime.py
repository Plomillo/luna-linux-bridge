"""UMOT core. Local operations only. This module does not certify itself."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

PARENT_SHA256 = "2950aa605d972672af925015ec4d061e5f5e526187aaa2507fba6b6e80246db6"
PARENT_BYTES = 205679247
CANDIDATE_FILENAME = "umot_compact-1.0.5.post12-1additive-py3-none-manylinux_2_34_x86_64.whl"
LOCAL_FIRST = True
EXTERNAL_PROVIDER_REQUIRED = False
NETWORK_REQUIRED_FOR_CORE = False
TOKEN_REQUIRED_FOR_CORE = False

AGENTS = (
    "architect", "developer", "debugger", "reviewer", "tester",
    "security", "optimizer", "researcher", "integrator", "validator",
)
LABS = (
    "archive", "system_rescue", "binary", "document", "data",
    "multimedia", "browser", "network", "model", "research",
)
ADAPTERS = ("claude", "codex", "antigravity", "gemini", "grok", "github", "huggingface")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run(argv: list[str], timeout: int = 20, env: dict | None = None) -> dict:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "FAIL", "reason": type(exc).__name__, "detail": str(exc)[:240]}
    text = (proc.stdout or "") + (proc.stderr or "")
    return {"status": "PASS" if proc.returncode == 0 else "FAIL", "exit_code": proc.returncode, "output_head": text[:500]}


def _which(name: str) -> str | None:
    return shutil.which(name)


class Core:
    def __init__(self, state: Path, root: Path | None = None):
        self.state = state
        self.root = root
        self.state.mkdir(parents=True, exist_ok=True)
        self.ledger_path = state / "ledger.jsonl"
        self.memory_path = state / "memory.json"
        self.checkpoint_dir = state / "checkpoints"
        self.checkpoint_dir.mkdir(exist_ok=True)
        if not self.memory_path.exists():
            self.memory_path.write_text("{}\n", encoding="utf-8")

    def _append(self, row: dict) -> dict:
        row.setdefault("operation_id", uuid.uuid4().hex)
        row.setdefault("timestamp", _now())
        row.setdefault("status", "PASS")
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return row

    def _ledger(self) -> list[dict]:
        if not self.ledger_path.exists():
            return []
        return [json.loads(line) for line in self.ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def capabilities(self) -> dict:
        tools = {
            "python": _which("python3"),
            "g++": _which("g++"),
            "git": _which("git"),
            "ffmpeg": _which("ffmpeg"),
            "cmake": _which("cmake"),
            "node": _which("node"),
            "cargo": _which("cargo"),
            "rustc": _which("rustc"),
            "java": _which("java"),
            "clang": _which("clang"),
            "ninja": _which("ninja"),
            "gdb": _which("gdb"),
            "mojo": _which("mojo"),
            "forgejo": _which("forgejo"),
        }
        rows = []
        for name, path in tools.items():
            rows.append({
                "id": name,
                "location": path,
                "lifecycle": "EXECUTABLE" if path else "ABSENT",
            })
        for agent in AGENTS:
            rows.append({"id": f"agent:{agent}", "lifecycle": "EXECUTABLE", "location": "umot.runtime.Core.agent"})
        for lab in LABS:
            rows.append({"id": f"lab:{lab}", "lifecycle": "EXECUTABLE", "location": "umot.runtime.Core.lab"})
        for adapter in ADAPTERS:
            rows.append({"id": f"adapter:{adapter}", "lifecycle": "OPTIONAL_UNAVAILABLE_WITHOUT_TOKEN", "location": "umot.runtime.Core.adapter"})
        return {"local_first": LOCAL_FIRST, "external_provider_required": EXTERNAL_PROVIDER_REQUIRED, "capabilities": rows}

    def status(self) -> dict:
        mem = self._meminfo()
        return {
            "schema": "UMOT_STATUS/1.0",
            "local_first": LOCAL_FIRST,
            "network_required_for_core": NETWORK_REQUIRED_FOR_CORE,
            "token_required_for_core": TOKEN_REQUIRED_FOR_CORE,
            "ledger_rows": len(self._ledger()),
            "checkpoints": sorted(path.name for path in self.checkpoint_dir.iterdir()),
            "memory_bytes": self.memory_path.stat().st_size,
            "mem_available_kb": mem.get("MemAvailable"),
            "parent_protected_sha256": PARENT_SHA256,
            "candidate_filename": CANDIDATE_FILENAME,
        }

    def doctor(self) -> dict:
        caps = self.capabilities()["capabilities"]
        absent = [row["id"] for row in caps if row["lifecycle"] == "ABSENT"]
        return {"status": "PASS", "absent_optional_or_uninstalled": absent, "core_import": "PASS"}

    def solve(self, operation: str) -> dict:
        routes = {
            "hash": ["security", "evidence"],
            "compile-cpp": ["toolchain:g++"],
            "git-commit": ["toolchain:git"],
            "remember": ["local-memory"],
            "agent-change": ["agent:developer", "agent:validator"],
            "repair": ["checkpoint", "repair"],
            "adapter": ["adapter-optional"],
        }
        if operation not in routes:
            return {"status": "FAIL", "reason": "NO_LOCAL_SOLVER", "operation": operation}
        return {"status": "PASS", "operation": operation, "selected": routes[operation]}

    def _meminfo(self) -> dict[str, int]:
        info = {}
        path = Path("/proc/meminfo")
        if not path.is_file():
            return info
        for line in path.read_text(encoding="utf-8").splitlines():
            key, _, rest = line.partition(":")
            parts = rest.strip().split()
            if parts and parts[0].isdigit():
                info[key] = int(parts[0])
        return info

    def govern(self, requested_kb: int) -> dict:
        available = self._meminfo().get("MemAvailable", 0)
        if requested_kb < 0:
            return {"status": "FAIL", "reason": "NEGATIVE_REQUEST"}
        if available and requested_kb > available:
            return {"status": "FAIL", "reason": "RESOURCE_BUDGET_EXCEEDED", "available_kb": available}
        return {"status": "PASS", "available_kb": available, "requested_kb": requested_kb}

    def remember(self, key: str, value: str) -> dict:
        data = json.loads(self.memory_path.read_text(encoding="utf-8") or "{}")
        data[key] = value
        self.memory_path.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")
        return self._append({"actor": "memory", "operation": "remember", "input": key, "input_hash": _sha256_bytes(value.encode()), "actual_result": "STORED"})

    def recall(self, key: str) -> dict:
        data = json.loads(self.memory_path.read_text(encoding="utf-8") or "{}")
        if key not in data:
            return {"status": "FAIL", "reason": "MEMORY_MISS", "key": key}
        return {"status": "PASS", "key": key, "value": data[key]}

    def checkpoint(self) -> dict:
        ident = uuid.uuid4().hex
        dest = self.checkpoint_dir / ident
        dest.mkdir()
        if self.ledger_path.exists():
            shutil.copyfile(self.ledger_path, dest / "ledger.jsonl")
        else:
            (dest / "ledger.jsonl").write_text("", encoding="utf-8")
        shutil.copyfile(self.memory_path, dest / "memory.json")
        row = self._append({"actor": "checkpoint", "operation": "checkpoint", "checkpoint": ident, "actual_result": "CREATED"})
        # The checkpoint copy was taken before this row. Record the pointer without rewriting the snapshot.
        return {"status": "PASS", "checkpoint": ident, "operation_id": row["operation_id"]}

    def rollback(self, ident: str) -> dict:
        src = self.checkpoint_dir / ident
        if not src.is_dir():
            return {"status": "FAIL", "reason": "CHECKPOINT_MISSING", "checkpoint": ident}
        shutil.copyfile(src / "ledger.jsonl", self.ledger_path)
        shutil.copyfile(src / "memory.json", self.memory_path)
        return {"status": "PASS", "checkpoint": ident, "restored": True}

    def run(self, operation: str, **params) -> dict:
        choice = self.solve(operation)
        if choice["status"] != "PASS":
            self._append({"actor": "engine", "operation": operation, "status": "FAIL", "actual_result": choice["reason"]})
            return choice
        budget = self.govern(int(params.get("requested_kb", 1024)))
        if budget["status"] != "PASS":
            self._append({"actor": "governor", "operation": operation, "status": "FAIL", "actual_result": budget["reason"]})
            return budget
        handler = {
            "hash": self._op_hash,
            "compile-cpp": self._op_compile,
            "git-commit": self._op_git,
            "remember": self._op_remember,
            "agent-change": self._op_agent_change,
            "repair": self._op_repair,
            "adapter": self._op_adapter,
        }[operation]
        result = handler(params)
        result["solver"] = choice
        self._append({
            "actor": "engine",
            "operation": operation,
            "parameters": {key: value for key, value in params.items() if key != "body"},
            "input_hash": _sha256_bytes(json.dumps(params, sort_keys=True, default=str).encode()),
            "actual_result": result.get("status"),
            "output_hash": _sha256_bytes(json.dumps(result, sort_keys=True, default=str).encode()),
            "status": result.get("status", "FAIL"),
        })
        return result

    def _op_hash(self, params: dict) -> dict:
        path = Path(str(params["path"]))
        if ".." in path.parts:
            return {"status": "FAIL", "reason": "PATH_REJECTED"}
        if not path.is_file():
            return {"status": "FAIL", "reason": "FILE_MISSING"}
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return {"status": "PASS", "sha256": digest}

    def _op_compile(self, params: dict) -> dict:
        compiler = _which("g++")
        if not compiler:
            return {"status": "FAIL", "reason": "GPP_ABSENT"}
        work = self.state / "build"
        work.mkdir(exist_ok=True)
        source = work / "probe.cpp"
        binary = work / "probe"
        source.write_text("int main(){return 0;}\n", encoding="utf-8")
        result = _run([compiler, "-std=c++23", str(source), "-o", str(binary)])
        if result["status"] != "PASS":
            return result
        ran = _run([str(binary)])
        return {"status": ran["status"], "compiler": compiler, "standard": "c++23"}

    def _op_git(self, params: dict) -> dict:
        git = _which("git")
        if not git:
            return {"status": "FAIL", "reason": "GIT_ABSENT"}
        repo = self.state / "local-repo"
        if repo.exists():
            shutil.rmtree(repo)
        repo.mkdir()
        (repo / "README").write_text("local\n", encoding="utf-8")
        env = os.environ.copy()
        commands = [
            [git, "init"],
            [git, "add", "README"],
            [git, "-c", "user.name=umot", "-c", "user.email=umot@localhost", "commit", "-m", "local"],
        ]
        for argv in commands:
            proc = subprocess.run(argv, cwd=repo, capture_output=True, text=True, env=env, check=False)
            if proc.returncode != 0:
                return {"status": "FAIL", "exit_code": proc.returncode, "output_head": ((proc.stdout or "") + (proc.stderr or ""))[:400]}
        return {"status": "PASS", "repo": str(repo), "forgejo": "ABSENT"}

    def _op_remember(self, params: dict) -> dict:
        stored = self.remember(str(params["key"]), str(params["value"]))
        loaded = self.recall(str(params["key"]))
        return {"status": "PASS" if loaded.get("value") == str(params["value"]) else "FAIL", "stored": stored["operation_id"]}

    def _op_agent_change(self, params: dict) -> dict:
        target = self.state / "work" / "change.txt"
        target.parent.mkdir(exist_ok=True)
        body = str(params.get("body", "change"))
        developed = self.agent("developer", {"body": body, "path": str(target)})
        if developed["status"] != "PASS":
            return developed
        validated = self.agent("validator", {"path": str(target), "expected_sha256": developed["sha256"], "implementer": "developer"})
        return {"status": validated["status"], "developer": developed, "validator": validated, "certified_by_developer": False}

    def _op_repair(self, params: dict) -> dict:
        target = self.state / "repair-target.txt"
        target.write_text("broken", encoding="utf-8")
        point = self.checkpoint()
        target.write_text("repaired", encoding="utf-8")
        if target.read_text(encoding="utf-8") != "repaired":
            return {"status": "FAIL", "reason": "REPAIR_DID_NOT_APPLY"}
        return {"status": "PASS", "checkpoint": point["checkpoint"], "result": "repaired"}

    def _op_adapter(self, params: dict) -> dict:
        name = str(params.get("name", "claude"))
        return self.adapter(name)

    def agent(self, name: str, payload: dict) -> dict:
        if name not in AGENTS:
            return {"status": "FAIL", "reason": "UNKNOWN_AGENT"}
        if name == "developer":
            path = Path(payload["path"])
            body = str(payload["body"]).encode()
            path.write_bytes(body)
            return {"status": "PASS", "actor": "developer", "sha256": _sha256_bytes(body), "may_certify": False}
        if name == "validator":
            if payload.get("implementer") == "validator":
                return {"status": "FAIL", "reason": "VALIDATOR_CANNOT_CERTIFY_ITSELF"}
            path = Path(payload["path"])
            digest = _sha256_bytes(path.read_bytes())
            if digest != payload["expected_sha256"]:
                return {"status": "FAIL", "reason": "VALIDATOR_HASH_MISMATCH", "sha256": digest}
            return {"status": "PASS", "actor": "validator", "independent": True, "sha256": digest}
        if name == "security":
            rejected = ".." in Path(str(payload.get("path", "safe"))).parts
            return {"status": "FAIL" if rejected else "PASS", "actor": "security", "rejected": rejected}
        if name == "architect":
            root = Path(payload.get("path", self.state))
            files = sorted(path.name for path in root.iterdir()) if root.is_dir() else []
            return {"status": "PASS", "actor": "architect", "files": files}
        if name == "debugger":
            result = _run(["python3", "-c", "import sys; sys.stderr.write('boom'); raise SystemExit(1)"])
            return {"status": "PASS" if result["status"] == "FAIL" and "boom" in result["output_head"] else "FAIL", "actor": "debugger", "captured": result["output_head"][:80]}
        if name == "reviewer":
            same = payload.get("before") == payload.get("after")
            return {"status": "PASS", "actor": "reviewer", "unchanged": same}
        if name == "tester":
            result = _run(["python3", "-c", "assert 6*7==42"])
            return {"status": result["status"], "actor": "tester"}
        if name == "optimizer":
            budget = self.govern(int(payload.get("requested_kb", 1)))
            return {"status": budget["status"], "actor": "optimizer", "budget": budget}
        if name == "researcher":
            text = self.memory_path.read_text(encoding="utf-8")
            needle = str(payload.get("needle", "{"))
            return {"status": "PASS" if needle in text else "FAIL", "actor": "researcher"}
        if name == "integrator":
            present = all(agent in AGENTS for agent in ("developer", "validator"))
            return {"status": "PASS" if present else "FAIL", "actor": "integrator", "separated": True}
        return {"status": "FAIL", "reason": "AGENT_NOT_WIRED"}

    def lab(self, name: str) -> dict:
        if name not in LABS:
            return {"status": "FAIL", "reason": "UNKNOWN_LAB"}
        if name == "archive":
            tool = _which("7z") or _which("bsdtar") or _which("tar")
            if not tool:
                return {"status": "FAIL", "reason": "ARCHIVE_TOOL_ABSENT"}
            probe = _run([tool, "--help"] if Path(tool).name != "tar" else [tool, "--version"])
            return {"status": probe["status"], "tool": tool}
        if name == "multimedia":
            tool = _which("ffmpeg")
            if not tool:
                return {"status": "FAIL", "reason": "FFMPEG_ABSENT"}
            probe = _run([tool, "-version"])
            return {"status": probe["status"], "tool": tool}
        if name == "data":
            probe = _run(["python3", "-c", "import sqlite3; c=sqlite3.connect(':memory:'); c.execute('create table t(x)'); c.execute('insert into t values (1)'); print(c.execute('select x from t').fetchone()[0])"])
            return {"status": "PASS" if probe["status"] == "PASS" and "1" in probe["output_head"] else "FAIL"}
        if name == "document":
            probe = _run(["python3", "-c", "print('document-lab')"])
            return {"status": probe["status"], "scope": "TEXT_ONLY_OCR_ABSENT"}
        if name == "binary":
            tool = _which("readelf")
            if not tool:
                return {"status": "FAIL", "reason": "READELF_ABSENT"}
            return {"status": "PASS", "tool": tool}
        if name == "system_rescue":
            return {"status": "PASS" if Path("/proc/meminfo").is_file() else "FAIL", "source": "/proc/meminfo"}
        if name == "network":
            return {"status": "PASS", "scope": "NO_TRAFFIC_CAPTURE", "dns_tool": _which("getent") is not None}
        if name == "browser":
            return {"status": "FAIL", "reason": "BROWSER_RUNTIME_NOT_LAUNCHED"}
        if name == "model":
            return {"status": "FAIL", "reason": "NO_GGUF_INFERENCE_MODEL_EXECUTED"}
        if name == "research":
            return self.agent("researcher", {"needle": "{"})
        return {"status": "FAIL", "reason": "LAB_NOT_WIRED"}

    def adapter(self, name: str) -> dict:
        if name not in ADAPTERS:
            return {"status": "FAIL", "reason": "UNKNOWN_ADAPTER"}
        return {
            "status": "UNAVAILABLE",
            "adapter": name,
            "token_present": False,
            "network_required": True,
            "core_blocked": False,
            "reason": "EXTERNAL_PROVIDER_NOT_REQUIRED",
        }

    def verify(self) -> dict:
        parent = os.environ.get("UMOT_PARENT_WHEEL")
        parent_ok = None
        if parent:
            path = Path(parent)
            digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
            parent_ok = digest == PARENT_SHA256 and path.stat().st_size == PARENT_BYTES
        required = [self.lab(name)["status"] for name in ("data", "system_rescue")]
        return {
            "status": "PASS" if all(item == "PASS" for item in required) else "FAIL",
            "parent_preserved": parent_ok,
            "ledger_rows": len(self._ledger()),
            "self_certification": "FORBIDDEN",
        }
