#!/usr/bin/env python3
"""Build derived installers that add an executable Luna agent.

The original LOUKSNA.deb and LOUKSNA.sh are not modified or replaced.
"""
from __future__ import annotations

import hashlib
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


MARKER = b"__LOUKSNA_ARCHIVE__\n"
WRAPPER = """#!/bin/sh
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
exec python3 "$ROOT/lib/louksna/luna/agent.py" "$@"
"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_luna(usr: Path, agent: Path) -> None:
    lib = usr / "lib" / "louksna" / "luna"
    lib.mkdir(parents=True, exist_ok=True)
    target = lib / "agent.py"
    shutil.copyfile(agent, target)
    target.chmod(0o755)
    bindir = usr / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    wrapper = bindir / "luna"
    wrapper.write_text(WRAPPER)
    wrapper.chmod(0o755)
    note = usr / "share" / "louksna" / "LUNA_DERIVED.txt"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(
        "identity=derived\n"
        "parent_package=louksna\n"
        "adds=/usr/bin/luna\n"
        "weight_training=NOT_AUTHORIZED\n"
        "self_certifies=false\n"
        "originals_not_replaced=true\n"
    )


def refresh_manifest(usr: Path) -> None:
    share = usr / "share" / "louksna"
    share.mkdir(parents=True, exist_ok=True)
    lines = []
    for path in sorted(usr.rglob("*")):
        if path.name in {"FILELIST.txt", "TREE_SHA256"}:
            continue
        if path.is_file() or path.is_symlink():
            lines.append(str(path.relative_to(usr.parent)))
    (share / "FILELIST.txt").write_text("\n".join(lines) + "\nusr/share/louksna/TREE_SHA256\n")
    digest = hashlib.sha256()
    for path in sorted(p for p in usr.rglob("*") if p.is_file() and not p.is_symlink()):
        if path.name == "TREE_SHA256":
            continue
        digest.update(str(path.relative_to(usr)).encode())
        digest.update(b"\0")
        digest.update(sha256(path).encode())
        digest.update(b"\n")
    (share / "TREE_SHA256").write_text(digest.hexdigest() + "\n")


def derive_deb(original: Path, agent: Path, dest: Path) -> None:
    work = Path(tempfile.mkdtemp(prefix="louksna-derived-deb-"))
    try:
        subprocess.check_call(["dpkg-deb", "-R", str(original), str(work)])
        add_luna(work / "usr", agent)
        refresh_manifest(work / "usr")
        control = work / "DEBIAN" / "control"
        text = control.read_text()
        text = text.replace("Version: 3.0.0\n", "Version: 3.0.0+luna1\n", 1)
        if "python3" not in text.split("Depends:", 1)[-1].split("\n", 1)[0]:
            text = text.replace(
                "Depends: libc6 (>= 2.34), libstdc++6, libgomp1, ca-certificates\n",
                "Depends: libc6 (>= 2.34), libstdc++6, libgomp1, ca-certificates, python3\n",
                1,
            )
        control.write_text(text)
        postinst = work / "DEBIAN" / "postinst"
        if postinst.is_file():
            body = postinst.read_text()
            body = body.replace(
                "chmod 755 /usr/bin/louksna-session",
                "chmod 755 /usr/bin/luna /usr/bin/louksna-session",
                1,
            )
            postinst.write_text(body)
            postinst.chmod(postinst.stat().st_mode | stat.S_IEXEC)
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(work), str(dest)])
    finally:
        shutil.rmtree(work, ignore_errors=True)


def derive_sh(original: Path, agent: Path, dest: Path) -> None:
    blob = original.read_bytes()
    at = blob.find(MARKER)
    if at < 0:
        raise SystemExit("SH_MARKER_ABSENT")
    header = blob[: at + len(MARKER)]
    archive = blob[at + len(MARKER) :]
    work = Path(tempfile.mkdtemp(prefix="louksna-derived-sh-"))
    try:
        raw = work / "payload.tar.xz"
        raw.write_bytes(archive)
        root = work / "root"
        root.mkdir()
        subprocess.check_call(["tar", "--no-same-owner", "-xJf", str(raw), "-C", str(root)])
        add_luna(root / "usr", agent)
        refresh_manifest(root / "usr")
        packed = work / "derived.tar.xz"
        with tarfile.open(packed, "w:xz") as tar:
            tar.add(root / "usr", arcname="usr")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(header + packed.read_bytes())
        dest.chmod(0o755)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    if len(sys.argv) != 5:
        print("usage: derive_installers.py LOUKSNA.deb LOUKSNA.sh agent.py outdir", file=sys.stderr)
        return 2
    deb = Path(sys.argv[1])
    sh = Path(sys.argv[2])
    agent = Path(sys.argv[3])
    out = Path(sys.argv[4])
    derived_deb = out / "LOUKSNA-luna-derived.deb"
    derived_sh = out / "LOUKSNA-luna-derived.sh"
    derive_deb(deb, agent, derived_deb)
    derive_sh(sh, agent, derived_sh)
    manifest = subprocess.check_output([sys.executable, str(agent), "--manifest"], text=True)
    (out / "derived-manifest-preview.json").write_text(manifest)
    lines = [
        f"{sha256(deb)}  original/LOUKSNA.deb",
        f"{sha256(sh)}  original/LOUKSNA.sh",
        f"{sha256(derived_deb)}  LOUKSNA-luna-derived.deb",
        f"{sha256(derived_sh)}  LOUKSNA-luna-derived.sh",
    ]
    (out / "DERIVED_SHA256SUMS").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
