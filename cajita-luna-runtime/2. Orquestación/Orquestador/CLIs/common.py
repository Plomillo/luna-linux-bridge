from __future__ import annotations
import hashlib
import os
import shutil
import subprocess
import time

def sha256_file(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None

def probe_version(binary, argv, timeout_seconds=20):
    env = os.environ.copy()
    resolved = shutil.which(binary, path=env.get("PATH"))
    if not resolved:
        return {"binary": binary, "argv": list(argv), "status": "ABSENT", "reason": "EXECUTABLE_NOT_FOUND", "shell": False}
    started = time.monotonic()
    try:
        result = subprocess.run([resolved, *list(argv)], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, timeout=max(1, min(int(timeout_seconds), 30)),
                                shell=False, env=env, check=False)
        stdout = (result.stdout or "")[:1600]
        stderr = (result.stderr or "")[:1000]
        return {"binary": binary, "resolved_path": resolved, "binary_sha256": sha256_file(resolved),
                "argv": list(argv), "returncode": result.returncode,
                "status": "PASS" if result.returncode == 0 else "NONZERO_EXIT",
                "stdout": stdout, "stderr": stderr, "elapsed_seconds": round(time.monotonic() - started, 3),
                "shell": False}
    except subprocess.TimeoutExpired:
        return {"binary": binary, "resolved_path": resolved, "argv": list(argv), "status": "TIMEOUT",
                "elapsed_seconds": round(time.monotonic() - started, 3), "shell": False}
    except OSError as exc:
        return {"binary": binary, "resolved_path": resolved, "argv": list(argv),
                "status": "EXECUTION_ERROR", "error_type": type(exc).__name__, "shell": False}

def probe_domain(domain_id, candidates):
    results = [probe_version(binary, argv) for binary, argv in candidates]
    available = [row for row in results if row["status"] == "PASS"]
    status = "AVAILABLE" if available else ("PARTIAL" if any(row["status"] not in {"ABSENT"} for row in results) else "ABSENT")
    return {"domain_id": domain_id, "status": status, "read_only": True, "mutations_performed": False,
            "probes": results, "certification": "NOT_GRANTED"}
