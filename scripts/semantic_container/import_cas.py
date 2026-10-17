#!/usr/bin/env python3
"""Verifiable, fail-closed CAS import for the private Louksna semantic container.

This helper NEVER authorizes operation, G23 or G24. It only reconstructs exact
CAS object bytes from an operator-authorized local directory or rclone remote.
Use an isolated Git checkout of staging/contenedor-semantico-e826-20260927.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED_COUNT = 252
EXPECTED_BYTES = 327745213
EXPECTED_MANIFEST_SHA256 = "c2daca06496353de517fc458b84ce6b41dedb0c486629419f149f7b676daad39"
REL = Path("artifacts/semantic-container")
OBJECTS = Path("18_HASH_INDEX/OBJECTS")
NAME = re.compile(r"^[0-9a-f]{64}$")


def die(message: str) -> None:
    raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(argv: list[str], *, cwd: Path) -> str:
    result = subprocess.run(argv, cwd=cwd, check=True, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout.strip()


def resolve_source(source_dir: str | None, rclone_source: str | None,
                   allow_network: bool, workdir: Path) -> Path:
    if bool(source_dir) == bool(rclone_source):
        die("Supply exactly one of --source-dir or --rclone-source.")
    if source_dir:
        p = Path(source_dir).expanduser()
        if p.is_symlink() or not p.is_dir():
            die("Local source missing or symbolic: " + str(p))
        root = p / OBJECTS if (p / OBJECTS).is_dir() else p
        if root.is_symlink() or not root.is_dir():
            die("Missing 18_HASH_INDEX/OBJECTS inside source.")
        if root.name != "OBJECTS":
            die("Source must be the container root or 18_HASH_INDEX/OBJECTS.")
        return root
    if not allow_network:
        die("rclone source requires explicit --allow-network.")
    if not shutil.which("rclone"):
        die("rclone is not installed. Install and authorize it separately.")
    if ":" not in rclone_source or rclone_source.startswith(":"):
        die("Expected explicit authorized rclone remote, e.g. gdrive:CONTENEDOR SEMANTICO")
    root = workdir / "OBJECTS"
    root.mkdir(parents=True, exist_ok=True)
    # rclone uses the *already configured* operator-authorized remote. No
    # tokens or credentials are read, printed, created or modified here.
    remote = rclone_source.rstrip("/") + "/18_HASH_INDEX/OBJECTS"
    run(["rclone", "copy", remote, str(root), "--checksum",
         "--retries", "2", "--transfers", "3"], cwd=workdir)
    return root


def load_manifest(repo: Path) -> tuple[list[dict], str]:
    path = repo / REL / "18_HASH_INDEX/CAS_MANIFEST.json"
    if not path.is_file() or path.is_symlink():
        die("Missing original CAS_MANIFEST.json")
    manifest_sha = sha256_file(path)
    if manifest_sha != EXPECTED_MANIFEST_SHA256:
        die("Original CAS manifest SHA-256 differs from recorded E825 evidence.")
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("content_addressed_payloads")
    if not isinstance(items, list) or len(items) != EXPECTED_COUNT:
        die("CAS manifest count mismatch.")
    if sum(x.get("bytes", -1) for x in items) != EXPECTED_BYTES:
        die("CAS manifest byte budget mismatch.")
    seen = set()
    for item in items:
        digest = item.get("sha256")
        relative = item.get("relative_payload")
        if not isinstance(digest, str) or not NAME.fullmatch(digest):
            die("Noncanonical digest in CAS manifest.")
        if relative != f"18_HASH_INDEX/OBJECTS/{digest[:2]}/{digest}":
            die("Noncanonical or unsafe CAS relative path: " + str(relative))
        if digest in seen:
            die("Duplicate CAS digest: " + digest)
        seen.add(digest)
        if type(item["bytes"]) is not int or item["bytes"] < 0:
            die("Invalid CAS size: " + digest)
    return items, manifest_sha


def verify_source(items: list[dict], source: Path) -> list[dict]:
    records = []
    for i, item in enumerate(items, 1):
        digest = item["sha256"]
        folder = source / digest[:2]
        path = folder / digest
        if folder.is_symlink() or not path.is_file() or path.is_symlink():
            die(f"MISSING_OR_SYMLINK: {digest}")
        stat_before = path.stat()
        if stat_before.st_size != item["bytes"]:
            die(f"SIZE_MISMATCH: {digest}")
        actual = sha256_file(path)
        stat_after = path.stat()
        if (stat_before.st_size != stat_after.st_size
                or stat_before.st_mtime_ns != stat_after.st_mtime_ns):
            die(f"SOURCE_CHANGED_DURING_HASH: {digest}")
        if actual != digest:
            die(f"SHA256_MISMATCH: {digest}")
        records.append({"sha256": digest, "bytes": item["bytes"]})
        if i % 25 == 0:
            print(f"VERIFIED {i}/{EXPECTED_COUNT}", flush=True)
    print(f"ALL_{EXPECTED_COUNT}_OBJECTS_SHA256_PASS total_bytes={EXPECTED_BYTES}",
          flush=True)
    return records


def import_exact(repo: Path, source: Path, items: list[dict],
                 report: list[dict], manifest_sha: str) -> None:
    if not shutil.which("git") or not shutil.which("git-lfs"):
        die("git and git-lfs are required; no packages are auto-installed.")
    git = lambda *args: run(["git", *args], cwd=repo)
    branch = git("branch", "--show-current")
    if branch != "staging/contenedor-semantico-e826-20260927":
        die("Import is only authorized on the dedicated staging branch.")
    if git("status", "--porcelain"):
        die("Git worktree must be clean; save all unrelated changes first.")
    checkpoint = git("rev-parse", "HEAD")
    print("CHECKPOINT_COMMIT " + checkpoint, flush=True)

    dest_root = repo / REL / OBJECTS
    # Source verification was completed *before* any repository modifications.
    for item in items:
        digest = item["sha256"]
        dst = dest_root / digest[:2] / digest
        dst.parent.mkdir(parents=True, exist_ok=True)
        src = source / digest[:2] / digest
        if dst.is_symlink():
            die("Refusing to overwrite symbolic destination: " + str(dst))
        if dst.exists() and sha256_file(dst) == digest:
            continue
        # Both input and copied output are verified, without replacing source.
        tmp = dst.with_name(dst.name + ".import-tmp")
        if tmp.exists() or tmp.is_symlink():
            die("Unexpected temporary file: " + str(tmp))
        try:
            with src.open("rb") as inp, tmp.open("xb") as out:
                shutil.copyfileobj(inp, out, 4 * 1024 * 1024)
            if tmp.stat().st_size != item["bytes"] or sha256_file(tmp) != digest:
                die("Copied bytes failed SHA-256: " + digest)
            os.replace(tmp, dst)
        finally:
            if tmp.exists():
                tmp.unlink()

    git("lfs", "install", "--local")
    git("lfs", "track", "artifacts/semantic-container/18_HASH_INDEX/OBJECTS/**")
    git("add", "--", ".gitattributes",
        "artifacts/semantic-container/18_HASH_INDEX/OBJECTS")
    # Convert the four small Git blobs imported during staging into LFS pointers.
    git("add", "--renormalize", "--",
        "artifacts/semantic-container/18_HASH_INDEX/OBJECTS")
    lfs_paths = set(git("lfs", "ls-files", "--name-only").splitlines())
    expected_paths = {
        (REL / item["relative_payload"]).as_posix() for item in items
    }
    missing = expected_paths - lfs_paths
    if missing:
        die(f"Not all CAS objects staged as Git LFS ({len(missing)} missing).")
    evidence = {
        "schema": "louksna.semantic-container.cas-import-report/v1",
        "checkpoint_commit": checkpoint,
        "manifest_sha256": manifest_sha,
        "object_count": EXPECTED_COUNT,
        "total_bytes": EXPECTED_BYTES,
        "content_sha256_verified": True,
        "git_lfs_paths_verified": True,
        "status": "LOCAL_IMPORT_STAGED_UNCERTIFIED",
        "g23": "NOT_EXECUTED",
        "g24": "NOT_EXECUTED",
        "files": report,
    }
    report_file = repo / REL / "CAS_IMPORT_REPORT.json"
    report_file.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    git("add", "--", str(report_file.relative_to(repo)))
    print("LOCAL_LFS_IMPORT_STAGED_CHECKPOINT " + checkpoint, flush=True)
    print("No push, merge, G23, G24 or operational activation performed.", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", help="local root of the original container")
    parser.add_argument("--rclone-source", help="pre-authorized remote root")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--mode", choices=("verify", "import"), default="verify")
    parser.add_argument("--authorize-import", action="store_true")
    parser.add_argument("--repo", type=Path,
                        default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve()
    items, manifest_sha = load_manifest(repo)
    with tempfile.TemporaryDirectory(prefix="louksna-cas-") as temp:
        root = resolve_source(args.source_dir, args.rclone_source,
                              args.allow_network, Path(temp))
        records = verify_source(items, root)
        if args.mode == "import":
            if not args.authorize_import:
                die("Import requires explicit --authorize-import.")
            import_exact(repo, root, items, records, manifest_sha)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError,
            RuntimeError) as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        sys.exit(2)
