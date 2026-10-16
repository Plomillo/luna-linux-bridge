#!/usr/bin/env python3
"""Inventario forense de solo lectura para SYMPHYLAX R1.

Alcance único: ~/SYMPHYLAX_LAB y tres scripts expresamente permitidos
en ~/ si existen. No ejecuta código del proyecto, no sigue enlaces
simbólicos, no lee contenido de archivos excluidos y no altera el origen.
Los resultados se escriben únicamente en RUNNER_TEMP de GitHub Actions.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path.home() / "SYMPHYLAX_LAB"
CANDIDATE_REL = Path(
    "CUSTOSZ_V7_R1_G23_G24_20260927T021532Z"
    "/R1_G23_ENGINEERED_F01_F06_CANDIDATE"
)
EXTRA = ("MISION_R1_G23_G24_600S.sh",
         "CERTIFICAR_R1_G23_G24.sh", "PREPARAR_F01_R1.sh")
OUTPUT = Path(os.environ["RUNNER_TEMP"]) / "symphylax-r1-evidence"
MAX_FILES = 30000
MAX_SINGLE_HASH = 512 * 1024 * 1024
MAX_TOTAL_HASH = 4 * 1024 * 1024 * 1024
BLOCK = 1024 * 1024

def prohibited(name):
    s = name.casefold()
    return (
        s in {".git", ".ssh", ".aws", ".config", ".gnupg",
              "__pycache__", ".venv", "venv", ".env", ".env.local"}
        or s.startswith(".env.")
        or any(x in s for x in ("secret", "credential", "password",
                                 "token", "private_key"))
        or s.endswith((".pem", ".p12", ".pfx", ".key", ".kdbx", ".log"))
        or s in {"id_rsa", "id_ed25519"}
    )

def sha_file(path, initial):
    # O_NOFOLLOW blocks a race that swaps a file for a symlink.
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb", buffering=0) as fh:
        before = os.fstat(fh.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError("file type changed during inventory")
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            initial.st_dev, initial.st_ino, initial.st_size, initial.st_mtime_ns
        ):
            raise RuntimeError("file changed before hashing")
        h = hashlib.sha256()
        while True:
            block = fh.read(BLOCK)
            if not block:
                break
            h.update(block)
        after = os.fstat(fh.fileno())
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
        ):
            raise RuntimeError("file changed during hashing")
        return h.hexdigest()

def main():
    if ROOT.is_symlink() or not ROOT.is_dir():
        raise RuntimeError("SYMPHYLAX_LAB missing or symlink: fail closed")
    candidate = ROOT / CANDIDATE_REL
    if candidate.is_symlink() or not candidate.is_dir():
        raise RuntimeError("expected SYMPHYLAX R1 candidate missing: fail closed")
    if OUTPUT.exists():
        raise RuntimeError("preexisting output: fail closed")
    OUTPUT.mkdir(parents=True, mode=0o700)
    counts = {
        "regular_files": 0, "symlinks_not_followed": 0,
        "excluded_sensitive_entries": 0, "hashed_files": 0,
        "unhashed_oversized_or_budget": 0, "other_nonregular": 0,
        "total_regular_bytes": 0, "total_hashed_bytes": 0,
        "outside_allowlist_present": 0
    }
    entries_path = OUTPUT / "files.jsonl"
    with entries_path.open("x", encoding="utf-8") as out:
        def record(path, relative):
            st = path.lstat()
            if stat.S_ISLNK(st.st_mode):
                counts["symlinks_not_followed"] += 1
                item = {"path": relative, "kind": "symlink_not_followed"}
            elif stat.S_ISREG(st.st_mode):
                counts["regular_files"] += 1
                counts["total_regular_bytes"] += st.st_size
                item = {"path": relative, "kind": "file",
                        "bytes": st.st_size, "mode": oct(stat.S_IMODE(st.st_mode)),
                        "mtime_utc": dt.datetime.fromtimestamp(
                            st.st_mtime, dt.timezone.utc).isoformat(),
                        "sha256": None, "hash_status": "NOT_HASHED"}
                if (st.st_size <= MAX_SINGLE_HASH
                        and counts["total_hashed_bytes"] + st.st_size <= MAX_TOTAL_HASH):
                    item["sha256"] = sha_file(path, st)
                    item["hash_status"] = "VERIFIED_STABLE_READ"
                    counts["hashed_files"] += 1
                    counts["total_hashed_bytes"] += st.st_size
                else:
                    counts["unhashed_oversized_or_budget"] += 1
            else:
                counts["other_nonregular"] += 1
                item = {"path": relative, "kind": "other_nonregular_skipped"}
            out.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
            if counts["regular_files"] > MAX_FILES:
                raise RuntimeError("file-count safety limit exceeded")

        for folder, dirs, files in os.walk(ROOT, topdown=True, followlinks=False):
            here = Path(folder)
            eligible = []
            for directory in sorted(dirs):
                p = here / directory
                if prohibited(directory):
                    counts["excluded_sensitive_entries"] += 1
                elif p.is_symlink():
                    record(p, "SYMPHYLAX_LAB/" + p.relative_to(ROOT).as_posix())
                else:
                    eligible.append(directory)
            dirs[:] = eligible
            for file in sorted(files):
                p = here / file
                if prohibited(file):
                    counts["excluded_sensitive_entries"] += 1
                else:
                    record(p, "SYMPHYLAX_LAB/" + p.relative_to(ROOT).as_posix())
        for name in EXTRA:
            p = Path.home() / name
            if p.exists() or p.is_symlink():
                if prohibited(name):
                    counts["excluded_sensitive_entries"] += 1
                else:
                    record(p, "HOME_ALLOWLIST/" + name)
                    counts["outside_allowlist_present"] += 1
    entry_sha = hashlib.sha256(entries_path.read_bytes()).hexdigest()
    manifest = {
        "schema": "SYMPHYLAX_R1_INVENTORY_1",
        "source_root": "~/SYMPHYLAX_LAB",
        "expected_candidate": "SYMPHYLAX_LAB/" + CANDIDATE_REL.as_posix(),
        "candidate_exists": True,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "github_repository": os.environ["GITHUB_REPOSITORY"],
        "workflow_commit": os.environ["GITHUB_SHA"],
        "workflow_run_id": os.environ["GITHUB_RUN_ID"],
        "runner_name": os.environ.get("RUNNER_NAME", "unknown"),
        "operation": "READ_ONLY_INVENTORY",
        "raw_source_files_uploaded": False,
        "scope": ["~/SYMPHYLAX_LAB", *["~/" + s for s in EXTRA]],
        "sha256_files_jsonl": entry_sha,
        "counts": counts,
        "G23": "HOLD_PENDING_INDEPENDENT_VALIDATION",
        "G24": "HOLD_PENDING_G23_AND_AUTHORITY",
        "certification": "NOT_GRANTED",
        "status": "PARTIAL_UNHASHED" if counts["unhashed_oversized_or_budget"] else "SCOPED_INVENTORY_EVIDENCED",
        "limitations": "Skipped sensitive names, symbolic links not followed; no source files copied or executed."
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    summary = {
        "status": manifest["status"], "regular_files": counts["regular_files"],
        "hashed_files": counts["hashed_files"],
        "excluded_sensitive_entries": counts["excluded_sensitive_entries"],
        "symlinks_not_followed": counts["symlinks_not_followed"],
        "unhashed_oversized_or_budget": counts["unhashed_oversized_or_budget"],
        "candidate_exists": True, "sha256_files_jsonl": entry_sha,
        "G23": manifest["G23"], "G24": manifest["G24"]
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("INVENTORY_ABORTED_FAIL_CLOSED: " + str(exc), file=sys.stderr)
        sys.exit(2)
