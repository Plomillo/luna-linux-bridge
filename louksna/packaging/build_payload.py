#!/usr/bin/env python3
"""Build LOUKSNA.deb and LOUKSNA.sh from one staged usr tree."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SESSION = ROOT / "louksna" / "session"
PACKAGING = ROOT / "louksna" / "packaging"
CACHE = Path(os.environ.get("LOUKSNA_CACHE", "/tmp/louksna-cache"))
WHISPER = Path(os.environ.get("LOUKSNA_WHISPER_BIN", "/tmp/whisper.cpp/build/bin/whisper-cli"))
BINARY = Path(os.environ.get("LOUKSNA_SESSION_BIN", str(SESSION / "target" / "release" / "louksna-session")))
OUT = Path(os.environ.get("LOUKSNA_DIST", str(ROOT / "dist")))
REFERENCE = ROOT / "LOUKSNA_ZONA_DIRECTIVA_GITHUB_INTERFACE_V0.2_HARDENED" / "images"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_file(src: Path, dest: Path, mode: int = 0o644) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    dest.chmod(mode)


def stage(tree: Path) -> None:
    usr = tree / "usr"
    copy_file(BINARY, usr / "bin" / "louksna-session", 0o755)
    copy_file(PACKAGING / "louksna-launch.sh", usr / "bin" / "louksna-launch", 0o755)
    lib = usr / "lib" / "louksna"
    copy_file(PACKAGING / "piper-wrapper.sh", lib / "piper-wrapper", 0o755)
    if not WHISPER.is_file():
        raise SystemExit(f"WHISPER_BIN_ABSENT {WHISPER}")
    copy_file(WHISPER, lib / "whisper-cli", 0o755)
    python_src = CACHE / "python"
    if not (python_src / "bin" / "python3").is_file():
        raise SystemExit(f"PYTHON_PREFIX_ABSENT {python_src}")
    shutil.copytree(python_src, lib / "python", symlinks=True)
    models = usr / "share" / "louksna" / "models"
    models.mkdir(parents=True)
    lock = json.loads((PACKAGING / "MODEL_LOCK.json").read_text())
    for name in ("es_ES-sharvard-medium.onnx", "es_ES-sharvard-medium.onnx.json", "ggml-tiny.bin"):
        src = CACHE / name
        digest = sha256(src)
        expected = lock[name]["sha256"]
        if digest != expected:
            raise SystemExit(f"MODEL_HASH_MISMATCH {name} {digest} != {expected}")
        copy_file(src, models / name)
    ui = usr / "share" / "louksna" / "ui"
    for name in ("index.html", "app.js", "styles.css", "icon.svg"):
        copy_file(SESSION / "ui" / name, ui / name)
    ref = usr / "share" / "louksna" / "reference"
    ref.mkdir(parents=True)
    if REFERENCE.is_dir():
        for image in REFERENCE.glob("*.png"):
            copy_file(image, ref / image.name)
    copy_file(PACKAGING / "MODEL_LOCK.json", usr / "share" / "louksna" / "MODEL_LOCK.json")
    copy_file(SESSION / "ui" / "icon.svg", usr / "share" / "icons" / "hicolor" / "scalable" / "apps" / "louksna.svg")
    copy_file(PACKAGING / "louksna.desktop", usr / "share" / "applications" / "louksna.desktop")
    copy_file(PACKAGING / "luna-session.service", usr / "lib" / "systemd" / "user" / "luna-session.service")
    (usr / "share" / "louksna" / "CERTIFICATION_STATUS.txt").write_text(
        "CERTIFICATION=NOT_CERTIFIED\n"
        "REASON=Debian 13 KDE Plasma Wayland physical session was not available in this build environment.\n"
        "G23_G24=EXECUTED_BY_SESSION_SELFTEST_WHEN_INSTALL_TEST_RUNS\n"
    )


def debianize(tree: Path) -> None:
    debian = tree / "DEBIAN"
    debian.mkdir()
    (debian / "control").write_text(
        "Package: louksna\n"
        "Version: 3.0.0\n"
        "Section: utils\n"
        "Priority: optional\n"
        "Architecture: amd64\n"
        "Maintainer: LOUKSNA <louksna@localhost>\n"
        "Depends: libc6 (>= 2.34), libstdc++6, libgomp1, ca-certificates\n"
        "Description: LOUKSNA Zona Directiva session\n"
        " Local LUNA runtime for Directiva V3. Loopback only.\n"
        " Not a certified release until KDE Plasma Wayland evidence exists.\n"
    )
    (debian / "postinst").write_text(
        "#!/bin/sh\nset -e\n"
        "chmod 755 /usr/bin/louksna-session /usr/bin/louksna-launch /usr/lib/louksna/piper-wrapper /usr/lib/louksna/whisper-cli || true\n"
        "echo 'LOUKSNA 3.0.0 installed. Certification: NOT_CERTIFIED until platform gates.'\n"
    )
    (debian / "prerm").write_text("#!/bin/sh\nset -e\nexit 0\n")
    (debian / "postrm").write_text(
        "#!/bin/sh\nset -e\n"
        "echo 'LOUKSNA removed. User state in ~/.local/share/louksna was kept.'\n"
    )
    for name in ("postinst", "prerm", "postrm"):
        (debian / name).chmod(0o755)


INSTALLER = r"""#!/bin/sh
set -eu
PREFIX=${PREFIX:-}
UNINSTALL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --prefix) PREFIX=$2; shift 2 ;;
    --uninstall) UNINSTALL=1; shift ;;
    *) echo "unknown arg $1" >&2; exit 2 ;;
  esac
done
if [ -z "$PREFIX" ]; then
  if [ "$(id -u)" -eq 0 ]; then PREFIX=/; else PREFIX=${HOME}/.local/louksna-root; fi
fi
MARKER=$(awk 'BEGIN{n=0} /^__LOUKSNA_ARCHIVE__$/ {print NR+1; exit}' "$0")
if [ "$UNINSTALL" -eq 1 ]; then
  if [ -f "$PREFIX/usr/share/louksna/FILELIST.txt" ]; then
    while IFS= read -r rel; do
      rm -f "$PREFIX/$rel"
    done < "$PREFIX/usr/share/louksna/FILELIST.txt"
  fi
  echo "LOUKSNA uninstalled from $PREFIX"
  exit 0
fi
mkdir -p "$PREFIX"
tail -n +"$MARKER" "$0" | tar -xJf - -C "$PREFIX"
echo "LOUKSNA installed under $PREFIX"
echo "Certification: NOT_CERTIFIED until Debian 13 KDE Plasma Wayland evidence exists."
exit 0
__LOUKSNA_ARCHIVE__
"""


def filelist(usr: Path) -> None:
    lines = []
    for path in sorted(usr.rglob("*")):
        if path.is_file() and not path.is_symlink():
            rel = path.relative_to(usr.parent)
            lines.append(str(rel))
        elif path.is_symlink():
            rel = path.relative_to(usr.parent)
            lines.append(str(rel))
    (usr / "share" / "louksna" / "FILELIST.txt").write_text("\n".join(lines) + "\nusr/share/louksna/TREE_SHA256\n")


def tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink()):
        if path.name == "TREE_SHA256":
            continue
        rel = str(path.relative_to(root)).encode()
        h.update(rel)
        h.update(b"\0")
        h.update(sha256(path).encode())
        h.update(b"\n")
    return h.hexdigest()


def main() -> None:
    if not BINARY.is_file():
        raise SystemExit(f"SESSION_BIN_ABSENT {BINARY}")
    OUT.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="louksna-stage-"))
    try:
        stage(work)
        filelist(work / "usr")
        digest = tree_digest(work / "usr")
        (work / "usr" / "share" / "louksna" / "TREE_SHA256").write_text(digest + "\n")
        debianize(work)
        deb = OUT / "LOUKSNA.deb"
        subprocess.check_call(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(work), str(deb)])
        tar_path = work / "payload.tar.xz"
        with tarfile.open(tar_path, "w:xz") as tar:
            tar.add(work / "usr", arcname="usr")
        sh_path = OUT / "LOUKSNA.sh"
        sh_path.write_bytes(INSTALLER.encode() + tar_path.read_bytes())
        sh_path.chmod(sh_path.stat().st_mode | stat.S_IEXEC)
        (OUT / "SHA256SUMS").write_text(
            f"{sha256(deb)}  LOUKSNA.deb\n{sha256(sh_path)}  LOUKSNA.sh\n{digest}  TREE\n"
        )
        verify(deb, sh_path, digest)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def verify(deb: Path, sh_path: Path, digest: str) -> None:
    base = Path(tempfile.mkdtemp(prefix="louksna-verify-"))
    deb_root = base / "deb"
    sh_root = base / "sh"
    deb_root.mkdir()
    sh_root.mkdir()
    subprocess.check_call(["dpkg-deb", "-x", str(deb), str(deb_root)])
    subprocess.check_call(["sh", str(sh_path), "--prefix", str(sh_root)])
    deb_digest = tree_digest(deb_root / "usr")
    sh_digest = tree_digest(sh_root / "usr")
    if deb_digest != digest or sh_digest != digest:
        raise SystemExit(f"PAYLOAD_PARITY_FAIL deb={deb_digest} sh={sh_digest} staged={digest}")
    (OUT / "PAYLOAD_PARITY_PASS").write_text(digest + "\n")
    env = os.environ.copy()
    env.update({
        "LOUKSNA_PIPER": str(deb_root / "usr/lib/louksna/piper-wrapper"),
        "LOUKSNA_WHISPER": str(deb_root / "usr/lib/louksna/whisper-cli"),
        "LOUKSNA_MODEL_DIR": str(deb_root / "usr/share/louksna/models"),
        "LOUKSNA_REQUIRE_SYNTHESIS": "1",
        "PYTHONNOUSERSITE": "1",
    })
    state = base / "state"
    report = subprocess.check_output([str(deb_root / "usr/bin/louksna-session"), "--selftest"], env=env, text=True)
    parsed = json.loads(report)
    if not parsed.get("ok") or parsed["checks"]["synthesis"]["verdict"] != "PASS":
        raise SystemExit("SELFTEST_FAIL\n" + report)
    wav = subprocess.check_output(
        [str(deb_root / "usr/bin/louksna-session"), "--state", str(state), "--speak", "Hola. Soy Luna."],
        env=env, text=True,
    ).strip()
    transcript = subprocess.check_output(
        [str(deb_root / "usr/bin/louksna-session"), "--state", str(state), "--transcribe", wav],
        env=env, text=True,
    ).strip().lower()
    if "luna" not in transcript and "hola" not in transcript:
        raise SystemExit(f"STT_UNEXPECTED {transcript!r}")
    launch = subprocess.run([str(deb_root / "usr/bin/louksna-launch")], env={**env, "XDG_SESSION_TYPE": "tty", "HOME": str(base)}, capture_output=True, text=True)
    if launch.returncode != 3 or "WAYLAND_REQUIRED" not in launch.stderr:
        raise SystemExit(f"WAYLAND_GATE_FAIL {launch.returncode} {launch.stderr}")
    (OUT / "VERIFY.json").write_text(json.dumps({
        "payload_parity": "PASS",
        "tree_sha256": digest,
        "selftest": parsed,
        "stt": transcript,
        "wayland_launcher_without_session": "BLOCKED_EXIT_3",
        "kde_plasma_physical": "NOT_RUN",
        "debian_13_physical": "NOT_RUN",
        "certification": "NOT_CERTIFIED",
    }, indent=2))
    print(json.dumps({"deb": str(deb), "sh": str(sh_path), "parity": digest, "stt": transcript}))


if __name__ == "__main__":
    main()
