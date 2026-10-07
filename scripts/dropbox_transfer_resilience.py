#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import py_compile
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SCHEMA_EVENT = "PUAC2_EVENT_RECORD_V2/1.0"
SCHEMA_CHECKPOINT = "PUAC2_DROPBOX_TRANSFER_CHECKPOINT/1.0"
SCHEMA_BUG = "PUAC2_TRANSFER_BUG_RECORD/1.0"
SCHEMA_RESEARCH = "PUAC2_LIVE_BUG_RESEARCH/1.0"
SCHEMA_BINDING = "PUAC2_TRANSFER_ARTIFACT_BINDING/1.0"

SAFE_STDLIB_IMPORTS = {
    "html": "import html",
    "hashlib": "import hashlib",
    "json": "import json",
    "os": "import os",
    "pathlib": "import pathlib",
    "re": "import re",
    "time": "import time",
    "traceback": "import traceback",
    "urllib": "import urllib",
    "zipfile": "import zipfile",
}

def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()

def atomic_json(path: pathlib.Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def canonical_hash(obj: Any) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def file_sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def emit_event(root: pathlib.Path, kind: str, **details: Any) -> dict:
    evid = root / "evidence"
    evid.mkdir(parents=True, exist_ok=True)
    state_path = evid / "EVENT_SEQUENCE.json"
    state = {"sequence_number": 0, "last_event_hash": None}
    if state_path.is_file():
        try:
            state.update(json.loads(state_path.read_text(encoding="utf-8")))
        except Exception:
            pass
    seq = int(state.get("sequence_number") or 0) + 1
    now = utc()
    event = {
        "schema": SCHEMA_EVENT,
        "event_id": f"{os.environ.get('GITHUB_RUN_ID','local')}:{seq}",
        "kind": kind,
        "event_time_utc": details.pop("event_time_utc", now),
        "observed_at_utc": details.pop("observed_at_utc", now),
        "recorded_at_utc": now,
        "sequence_number": seq,
        "causal_parents": [state["last_event_hash"]] if state.get("last_event_hash") else [],
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "commit_sha": os.environ.get("GITHUB_SHA"),
        "details": details,
    }
    event_hash = canonical_hash(event)
    event["event_hash"] = event_hash
    with (evid / "EVENTS_V2.ndjson").open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
    atomic_json(state_path, {"sequence_number": seq, "last_event_hash": event_hash})
    return event

def verify_checkpoint_obj(cp: dict) -> bool:
    expected = cp.get("checkpoint_hash")
    if not expected:
        return False
    body = dict(cp)
    body.pop("checkpoint_hash", None)
    return canonical_hash(body) == expected

def load_checkpoint(path: pathlib.Path) -> dict:
    cp = json.loads(path.read_text(encoding="utf-8"))
    if cp.get("schema") != SCHEMA_CHECKPOINT:
        raise RuntimeError("CHECKPOINT_SCHEMA_MISMATCH")
    if not verify_checkpoint_obj(cp):
        raise RuntimeError("CHECKPOINT_HASH_MISMATCH")
    return cp

def write_checkpoint(
    root: pathlib.Path,
    manifest: dict,
    queue: list[dict],
    completed_keys: set[str],
    reason: str,
    failed: list[dict] | None = None,
    parent_hint: str | None = None,
) -> dict:
    cps = root / "checkpoints"
    cps.mkdir(parents=True, exist_ok=True)
    latest = cps / "LATEST.json"
    parent_hash = parent_hint
    previous_seq = 0
    if latest.is_file():
        try:
            prev = load_checkpoint(latest)
            parent_hash = prev["checkpoint_hash"]
            previous_seq = int(prev.get("checkpoint_sequence") or 0)
        except Exception:
            pass
    cp = {
        "schema": SCHEMA_CHECKPOINT,
        "status": "VERIFIED_CHECKPOINT",
        "authority": "Louksna.md",
        "governance": "PUAC2.md",
        "checkpoint_id": f"CP-{os.environ.get('GITHUB_RUN_ID','local')}-{previous_seq + 1:06d}",
        "checkpoint_sequence": previous_seq + 1,
        "parent_checkpoint_hash": parent_hash,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "commit_sha": os.environ.get("GITHUB_SHA"),
        "environment_id": "GITHUB_HOSTED_UBUNTU_24_04",
        "created_at_utc": utc(),
        "reason": reason,
        "completed_keys": sorted(completed_keys),
        "pending_queue": queue,
        "failed": failed or [],
        "manifest_snapshot": manifest,
        "recovery_plan_v2": {
            "authorized_actor": "CUSTOSZ_V7_GOVERNED_EXECUTION",
            "checkpoint_id": None,
            "checkpoint_hash": None,
            "target_environment": "GITHUB_HOSTED_UBUNTU_24_04",
            "dependency_hashes": [],
            "restoration_oracles": [
                "CHECKPOINT_HASH_MATCH",
                "SOURCE_IDENTITY_MATCH",
                "PAYLOAD_HASH_OR_ARTIFACT_DIGEST_MATCH",
                "QUEUE_RECONCILIATION",
            ],
            "nonregression_plan": "TARGETED_TESTS_THEN_GLOBAL_TRANSFER_CONTRACT",
            "rollback_scope": "TRANSFER_STATE_ONLY",
            "irreversible_side_effects": [],
            "authority_ref": "Louksna.md + PUAC2.md",
        },
    }
    cp["recovery_plan_v2"]["checkpoint_id"] = cp["checkpoint_id"]
    cp["checkpoint_hash"] = canonical_hash(cp)
    cp["recovery_plan_v2"]["checkpoint_hash"] = cp["checkpoint_hash"]
    # Re-hash after binding the recovery plan to the first hash.
    body = dict(cp)
    body.pop("checkpoint_hash", None)
    cp["checkpoint_hash"] = canonical_hash(body)
    cp["recovery_plan_v2"]["checkpoint_hash"] = cp["checkpoint_hash"]
    # Final hash must cover the final recovery-plan value.
    body = dict(cp)
    body.pop("checkpoint_hash", None)
    cp["checkpoint_hash"] = canonical_hash(body)
    # recovery_plan_v2 is informative and references the final checkpoint hash.
    cp["recovery_plan_v2"]["checkpoint_hash"] = cp["checkpoint_hash"]
    # Hash excluding checkpoint_hash but including recovery_plan causes recursion if exact;
    # therefore verification normalizes the embedded convenience copy.
    cp["_hash_normalization"] = "RECOVERY_PLAN_CHECKPOINT_HASH_EXCLUDED"
    body = dict(cp)
    body.pop("checkpoint_hash", None)
    rp = dict(body.get("recovery_plan_v2") or {})
    rp["checkpoint_hash"] = None
    body["recovery_plan_v2"] = rp
    body.pop("_hash_normalization", None)
    cp["checkpoint_hash"] = canonical_hash(body)
    cp["recovery_plan_v2"]["checkpoint_hash"] = cp["checkpoint_hash"]
    cp["_hash_normalization"] = "RECOVERY_PLAN_CHECKPOINT_HASH_EXCLUDED"

    def normalized_hash(obj: dict) -> str:
        body2 = dict(obj)
        body2.pop("checkpoint_hash", None)
        body2.pop("_hash_normalization", None)
        rp2 = dict(body2.get("recovery_plan_v2") or {})
        rp2["checkpoint_hash"] = None
        body2["recovery_plan_v2"] = rp2
        return canonical_hash(body2)

    cp["checkpoint_hash"] = normalized_hash(cp)
    cp["recovery_plan_v2"]["checkpoint_hash"] = cp["checkpoint_hash"]
    name = cps / f"{cp['checkpoint_sequence']:06d}_{cp['checkpoint_id']}.json"
    atomic_json(name, cp)
    atomic_json(latest, cp)
    with (cps / "CHECKPOINT_CHAIN.ndjson").open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "checkpoint_id": cp["checkpoint_id"],
            "checkpoint_hash": cp["checkpoint_hash"],
            "parent_checkpoint_hash": cp["parent_checkpoint_hash"],
            "recorded_at_utc": utc(),
        }, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
    emit_event(root, "CHECKPOINT_COMMITTED", checkpoint_id=cp["checkpoint_id"], checkpoint_hash=cp["checkpoint_hash"], reason=reason)
    return cp

def verify_checkpoint_obj(cp: dict) -> bool:
    expected = cp.get("checkpoint_hash")
    if not expected:
        return False
    body = dict(cp)
    body.pop("checkpoint_hash", None)
    body.pop("_hash_normalization", None)
    rp = dict(body.get("recovery_plan_v2") or {})
    rp["checkpoint_hash"] = None
    body["recovery_plan_v2"] = rp
    return canonical_hash(body) == expected

def _binding_valid(binding: dict | None) -> bool:
    return bool(
        binding
        and str(binding.get("artifact_id") or "").strip()
        and str(binding.get("artifact_digest") or "").startswith("sha256:")
        and int(binding.get("artifact_size_bytes") or 0) >= 0
    )

def load_resume_state(
    seed_path: str | None,
    checkpoint_path: str | None,
    artifact_binding_path: str | None,
    link_key,
) -> dict:
    current_run = str(os.environ.get("GITHUB_RUN_ID") or "")
    state = {
        "completed_keys": set(),
        "prior_completed": [],
        "current_completed": [],
        "pending_queue": [],
        "split_folders": [],
        "parent_checkpoint_hash": None,
        "source": [],
    }

    if seed_path:
        p = pathlib.Path(seed_path)
        if p.is_file():
            seed = json.loads(p.read_text(encoding="utf-8"))
            for item in seed.get("completed", []):
                if item.get("evidence_status") != "COMPLETED_VERIFIED_PRIOR_RUN":
                    continue
                if not str(item.get("artifact_digest") or "").startswith("sha256:"):
                    continue
                if int(item.get("artifact_size_bytes") or 0) <= 0:
                    continue
                key = link_key(item["source_url"])
                state["completed_keys"].add(key)
                record = dict(item)
                record["source_identity_sha256"] = key
                record.pop("source_url", None)
                state["prior_completed"].append(record)
            state["source"].append("BOOTSTRAP_SEED")

    binding = None
    if artifact_binding_path:
        bp = pathlib.Path(artifact_binding_path)
        if bp.is_file():
            try:
                binding = json.loads(bp.read_text(encoding="utf-8"))
            except Exception:
                binding = None

    if checkpoint_path:
        cp_path = pathlib.Path(checkpoint_path)
        if cp_path.is_file():
            cp = load_checkpoint(cp_path)
            state["parent_checkpoint_hash"] = cp["checkpoint_hash"]
            snap = cp.get("manifest_snapshot") or {}
            same_run = str(cp.get("run_id") or "") == current_run and bool(current_run)
            prior_keys = set(cp.get("completed_keys") or [])
            if same_run:
                state["completed_keys"].update(prior_keys)
                state["current_completed"].extend(snap.get("completed") or [])
                state["prior_completed"].extend(snap.get("prior_completed") or [])
                state["split_folders"].extend(snap.get("split_folders") or [])
                state["pending_queue"] = cp.get("pending_queue") or []
                state["source"].append("SAME_RUN_CHECKPOINT")
            elif _binding_valid(binding):
                state["completed_keys"].update(prior_keys)
                state["prior_completed"].extend(snap.get("prior_completed") or [])
                for item in snap.get("completed") or []:
                    rec = dict(item)
                    rec["evidence_status"] = "COMPLETED_VERIFIED_PRIOR_RUN"
                    rec["artifact_binding"] = binding
                    state["prior_completed"].append(rec)
                state["split_folders"].extend(snap.get("split_folders") or [])
                state["pending_queue"] = cp.get("pending_queue") or []
                state["source"].append("PRIOR_RUN_CHECKPOINT_WITH_ARTIFACT_BINDING")
    return state

def load_fix_kb() -> dict:
    explicit = os.environ.get("TRANSFER_FIX_KB", "").strip()
    candidates = []
    if explicit:
        candidates.append(pathlib.Path(explicit))
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    candidates.append(repo_root / "mission-control" / "dropbox-github-cloud-partitioned" / "TRANSFER_FIX_KB.json")
    for path in candidates:
        if path.is_file():
            try:
                kb = json.loads(path.read_text(encoding="utf-8"))
                if kb.get("schema") == "PUAC2_TRANSFER_FIX_KB/1.0":
                    return kb
            except Exception:
                pass
    return {"schema":"PUAC2_TRANSFER_FIX_KB/1.0","status":"UNAVAILABLE","entries":[]}


def lookup_known_fix(category: str, signal: str) -> dict | None:
    kb = load_fix_kb()
    for entry in kb.get("entries", []):
        if entry.get("category") != category:
            continue
        if not str(entry.get("validation_status") or "").startswith("VALIDATED"):
            continue
        pattern = str(entry.get("signal_regex") or "")
        try:
            matched = bool(pattern and re.search(pattern, signal, flags=re.I))
        except re.error:
            matched = False
        if matched:
            return entry
    return None


def classify_bug(stderr_text: str) -> tuple[str, str, str | None]:
    text = stderr_text[-16000:]
    lower = text.lower()
    m = re.search(r"NameError:\s*name ['\"]([^'\"]+)['\"] is not defined", text)
    if m:
        missing = m.group(1)
        return "CODE_NAMEERROR", "RUNTIME_PATCH_STANDARD_IMPORT" if missing in SAFE_STDLIB_IMPORTS else "RETRY_FROM_CHECKPOINT_ONCE", missing
    if "record_event() got multiple values for argument 'kind'" in text:
        return "CODE_EVENT_KIND_COLLISION", "RUNTIME_PATCH_EVENT_KIND_COLLISION", None
    if "partition_required_but_children_empty" in lower or "dropbox_api_authoritative_inventory" in lower:
        return "DROPBOX_SHARED_FOLDER_INVENTORY_INCOMPATIBLE", "GOVERNED_API_THEN_HYDRATED_PUBLIC_INVENTORY", None
    if "action-bar-download-button" in lower or "folder_download_ui_control_unavailable" in lower or "ui_control_unavailable_after_direct_dl1" in lower:
        return "DROPBOX_UI_SELECTOR_DRIFT", "DIRECT_DL1_THEN_SPLIT", None
    if any(x in lower for x in ["too many files", "partition_not_zip", "returned_html", "folder_download_no_material", "continuation_not_found"]):
        return "PARTITION_STRATEGY", "SPLIT_FALLBACK_AND_RETRY", None
    if any(x in lower for x in ["timed out", "timeout", "connection reset", "remote end closed", "temporary failure", "429", "502", "503", "504"]):
        return "TRANSIENT_NETWORK", "RETRY_BACKOFF", None
    if "curl: (23)" in lower or "failure writing output" in lower:
        return "DROPBOX_PUBLIC_DL1_WRITE_INTERRUPTION", "ISOLATED_CURL_RETRY_VALIDATE_ZIP_CRC", None
    if any(x in lower for x in ["no space left", "enospc"]):
        return "IO_STORAGE", "CLEAN_PARTIAL_AND_RETRY", None
    if "root_children_empty" in lower or "children_empty" in lower:
        return "INVENTORY_FAILURE", "RELOAD_INVENTORY_AND_RETRY", None
    return "UNKNOWN_TRANSFER_BUG", "RETRY_FROM_CHECKPOINT_ONCE", None

def _http_json(url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> Any:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Louksna-PUAC2-LiveBugResolver/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))

def live_research(signal: str) -> dict:
    query = re.sub(r"\s+", " ", signal.strip())[-350:]
    results: list[dict] = []
    errors: list[dict] = []
    token = os.environ.get("GITHUB_TOKEN", "")
    gh_headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Louksna-PUAC2-LiveBugResolver/1.0",
    }
    if token:
        gh_headers["Authorization"] = "Bearer " + token
    try:
        q = urllib.parse.quote(query + " is:issue")
        data = _http_json(f"https://api.github.com/search/issues?q={q}&per_page=5", gh_headers)
        for item in data.get("items", [])[:5]:
            results.append({
                "source": "GITHUB_ISSUES_LIVE",
                "title": item.get("title"),
                "url": item.get("html_url"),
                "state": item.get("state"),
            })
    except Exception as e:
        errors.append({"source": "GITHUB_ISSUES_LIVE", "error": f"{type(e).__name__}:{e}"})

    try:
        q = urllib.parse.urlencode({
            "site": "stackoverflow",
            "order": "desc",
            "sort": "relevance",
            "q": query[:250],
            "pagesize": 5,
        })
        data = _http_json("https://api.stackexchange.com/2.3/search/advanced?" + q)
        for item in data.get("items", [])[:5]:
            results.append({
                "source": "STACKOVERFLOW_LIVE",
                "title": item.get("title"),
                "url": item.get("link"),
                "score": item.get("score"),
                "is_answered": item.get("is_answered"),
            })
    except Exception as e:
        errors.append({"source": "STACKOVERFLOW_LIVE", "error": f"{type(e).__name__}:{e}"})

    try:
        q = urllib.parse.quote(query[:300])
        req = urllib.request.Request(
            "https://html.duckduckgo.com/html/?q=" + q,
            headers={"User-Agent": "Mozilla/5.0 Louksna-PUAC2-LiveBugResolver/1.0"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        for href, title in re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.I | re.S)[:5]:
            title = re.sub(r"<[^>]+>", "", title)
            results.append({"source": "WEB_SEARCH_LIVE", "title": title, "url": href})
    except Exception as e:
        errors.append({"source": "WEB_SEARCH_LIVE", "error": f"{type(e).__name__}:{e}"})

    return {
        "schema": SCHEMA_RESEARCH,
        "query": query,
        "searched_at_utc": utc(),
        "results": results,
        "errors": errors,
        "live_search_performed": True,
    }

def diagnose(stderr_path: pathlib.Path, out_dir: pathlib.Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.is_file() else ""
    nonempty = [x.strip() for x in text.splitlines() if x.strip()]
    signal = " | ".join(nonempty[-8:])[-2000:] or "unknown transfer failure"
    category, action, missing = classify_bug(text)
    fingerprint = hashlib.sha256((category + "\n" + signal).encode("utf-8")).hexdigest()
    known_fix = lookup_known_fix(category, signal)
    if known_fix:
        action = str(known_fix.get("action") or action)
        research = {
            "schema": SCHEMA_RESEARCH,
            "query": signal,
            "searched_at_utc": utc(),
            "results": [],
            "errors": [],
            "live_search_performed": False,
            "research_skipped_reason": "KNOWN_VERIFIED_FIX",
            "known_fix_id": known_fix.get("fix_id"),
        }
    else:
        research = live_research(signal)
    bug = {
        "schema": SCHEMA_BUG,
        "bug_id": "BUG-" + fingerprint[:16],
        "bug_fingerprint": fingerprint,
        "category": category,
        "recommended_action": action,
        "missing_symbol": missing,
        "signal": signal,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "commit_sha": os.environ.get("GITHUB_SHA"),
        "environment_id": "GITHUB_HOSTED_UBUNTU_24_04",
        "first_seen_utc": utc(),
        "evidence_preserved": True,
        "live_research_file": "LIVE_RESEARCH.json",
        "live_research_result_count": len(research["results"]),
        "known_fix_reused": bool(known_fix),
        "known_fix_id": known_fix.get("fix_id") if known_fix else None,
        "known_fix_validation_status": known_fix.get("validation_status") if known_fix else None,
        "status": "DIAGNOSED",
    }
    atomic_json(out_dir / "BUG_RECORD.json", bug)
    atomic_json(out_dir / "LIVE_RESEARCH.json", research)
    print(json.dumps(bug, sort_keys=True))
    return bug

def apply_safe_runtime_repair(target: pathlib.Path, bug_path: pathlib.Path, out_path: pathlib.Path) -> dict:
    bug = json.loads(bug_path.read_text(encoding="utf-8"))
    result = {
        "schema": "PUAC2_SAFE_RUNTIME_REPAIR/1.0",
        "status": "NOT_APPLIED",
        "target": str(target),
        "bug_id": bug.get("bug_id"),
        "applied_at_utc": utc(),
    }
    action = bug.get("recommended_action")
    if action == "RUNTIME_PATCH_EVENT_KIND_COLLISION":
        source = target.read_text(encoding="utf-8")
        patched = source.replace('kind=item["kind"],', 'item_kind=item["kind"],')
        patched = patched.replace('record_event("DOWNLOAD_EVENT", kind=kind,', 'record_event("DOWNLOAD_EVENT", source_kind=kind,')
        if patched == source:
            result["status"] = "DENIED_NO_COLLISION_PATTERN"
            atomic_json(out_path, result)
            return result
        original_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
        target.write_text(patched, encoding="utf-8")
        try:
            py_compile.compile(str(target), doraise=True)
        except Exception:
            target.write_text(source, encoding="utf-8")
            result["status"] = "ROLLBACK_AFTER_COMPILE_FAILURE"
            atomic_json(out_path, result)
            return result
        result.update({
            "status": "PASS",
            "repair_type": "EVENT_KIND_KEYWORD_COLLISION",
            "original_sha256": original_hash,
            "patched_sha256": file_sha256(target),
            "targeted_test": "PY_COMPILE_PASS",
            "persistent_repo_mutation": False,
        })
        atomic_json(out_path, result)
        return result
    if action != "RUNTIME_PATCH_STANDARD_IMPORT":
        atomic_json(out_path, result)
        return result
    missing = str(bug.get("missing_symbol") or "")
    import_line = SAFE_STDLIB_IMPORTS.get(missing)
    if not import_line:
        atomic_json(out_path, result)
        return result
    source = target.read_text(encoding="utf-8")
    if re.search(rf"^\s*import\s+{re.escape(missing)}(?:\s|$)", source, re.M) or re.search(rf"^\s*from\s+{re.escape(missing)}\s+import\s+", source, re.M):
        result["status"] = "ALREADY_PRESENT"
        atomic_json(out_path, result)
        return result
    marker = "from __future__ import annotations\n"
    if marker not in source:
        result["status"] = "DENIED_NO_SAFE_INSERTION_POINT"
        atomic_json(out_path, result)
        return result
    patched = source.replace(marker, marker + "\n" + import_line + "\n", 1)
    original_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    target.write_text(patched, encoding="utf-8")
    try:
        py_compile.compile(str(target), doraise=True)
    except Exception:
        target.write_text(source, encoding="utf-8")
        result["status"] = "ROLLBACK_AFTER_COMPILE_FAILURE"
        atomic_json(out_path, result)
        return result
    result.update({
        "status": "PASS",
        "repair_type": "SAFE_STDLIB_IMPORT",
        "missing_symbol": missing,
        "original_sha256": original_hash,
        "patched_sha256": file_sha256(target),
        "targeted_test": "PY_COMPILE_PASS",
        "persistent_repo_mutation": False,
    })
    atomic_json(out_path, result)
    return result

def bind_artifact(root: pathlib.Path, out_dir: pathlib.Path, artifact_id: str, artifact_name: str, artifact_digest: str, artifact_size_bytes: int, run_id: str) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_digest = str(artifact_digest or "")
    if artifact_digest and not artifact_digest.startswith("sha256:"):
        artifact_digest = "sha256:" + artifact_digest
    latest = root / "checkpoints" / "LATEST.json"
    if not latest.is_file():
        raise SystemExit("LATEST_CHECKPOINT_MISSING_FOR_BINDING")
    cp = load_checkpoint(latest)
    shutil.copy2(latest, out_dir / "LATEST.json")
    chain = root / "checkpoints" / "CHECKPOINT_CHAIN.ndjson"
    if chain.is_file():
        shutil.copy2(chain, out_dir / "CHECKPOINT_CHAIN.ndjson")
    binding = {
        "schema": SCHEMA_BINDING,
        "status": "PASS",
        "artifact_id": str(artifact_id),
        "artifact_name": artifact_name,
        "artifact_digest": artifact_digest,
        "artifact_size_bytes": int(artifact_size_bytes),
        "run_id": str(run_id),
        "checkpoint_id": cp["checkpoint_id"],
        "checkpoint_hash": cp["checkpoint_hash"],
        "bound_at_utc": utc(),
    }
    atomic_json(out_dir / "RUN_ARTIFACT_BINDING.json", binding)
    return binding

def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("diagnose")
    d.add_argument("--stderr", required=True)
    d.add_argument("--out", required=True)

    p = sub.add_parser("apply-safe-runtime-repair")
    p.add_argument("--target", required=True)
    p.add_argument("--bug", required=True)
    p.add_argument("--out", required=True)

    v = sub.add_parser("verify-checkpoint")
    v.add_argument("--checkpoint", required=True)

    b = sub.add_parser("bind-artifact")
    b.add_argument("--root", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--artifact-id", required=True)
    b.add_argument("--artifact-name", required=True)
    b.add_argument("--artifact-digest", required=True)
    b.add_argument("--artifact-size-bytes", required=True, type=int)
    b.add_argument("--run-id", required=True)

    args = ap.parse_args()
    if args.cmd == "diagnose":
        diagnose(pathlib.Path(args.stderr), pathlib.Path(args.out))
    elif args.cmd == "apply-safe-runtime-repair":
        result = apply_safe_runtime_repair(pathlib.Path(args.target), pathlib.Path(args.bug), pathlib.Path(args.out))
        print(json.dumps(result, sort_keys=True))
    elif args.cmd == "verify-checkpoint":
        cp = load_checkpoint(pathlib.Path(args.checkpoint))
        print(json.dumps({"status": "PASS", "checkpoint_id": cp["checkpoint_id"], "checkpoint_hash": cp["checkpoint_hash"]}, sort_keys=True))
    elif args.cmd == "bind-artifact":
        result = bind_artifact(
            pathlib.Path(args.root), pathlib.Path(args.out),
            args.artifact_id, args.artifact_name, args.artifact_digest,
            args.artifact_size_bytes, args.run_id,
        )
        print(json.dumps(result, sort_keys=True))

if __name__ == "__main__":
    main()
