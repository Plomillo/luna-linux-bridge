#!/usr/bin/env python3
from pathlib import Path
import gzip
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

if len(sys.argv) != 2:
    raise SystemExit("usage: louksna_zd_v03_deb_sanitize.py <deb>")

deb=Path(sys.argv[1]).resolve()
if not deb.is_file():
    raise SystemExit("DEB_NOT_FOUND")

with tempfile.TemporaryDirectory(prefix="louksna-v03-sanitize-") as td:
    stage=Path(td)/"stage"
    subprocess.run(["dpkg-deb","-R",str(deb),str(stage)],check=True)

    control=stage/"DEBIAN"/"control"
    text=control.read_text(encoding="utf-8")
    text=re.sub(
        r"(?ms)^Description:.*?(?=^[A-Za-z0-9-]+:|\\Z)",
        "Description: LOUKSNA Zona Directiva functional interface\n"
        " Functional candidate with local evidence and persistent settings.\n"
        " GitHub read-only access is governed and explicitly authenticated.\n",
        text
    )
    control.write_text(text,encoding="utf-8")

    doc=stage/"usr"/"share"/"doc"/"louksna-zona-directiva"
    doc.mkdir(parents=True,exist_ok=True)
    changelog=(
        "louksna-zona-directiva (0.3.0) experimental; urgency=medium\n\n"
        "  * Functional candidate with local SQLite state.\n"
        "  * GitHub read-only integration and evidence ledger.\n\n"
        " -- Louksna Project <louksna@example.invalid>  Tue, 06 Oct 2026 07:30:00 +0000\n"
    ).encode("utf-8")
    with gzip.GzipFile(filename="",mode="wb",fileobj=(doc/"changelog.gz").open("wb"),mtime=0) as gz:
        gz.write(changelog)

    man=stage/"usr"/"share"/"man"/"man1"
    man.mkdir(parents=True,exist_ok=True)
    man_text=(
        '.TH LOUKSNA-ZONA-DIRECTIVA 1 "October 2026" "LOUKSNA 0.3.0" "User Commands"\n'
        '.SH NAME\n'
        'louksna-zona-directiva \\- governed desktop interface for LOUKSNA\n'
        '.SH SYNOPSIS\n'
        '.B louksna-zona-directiva\n'
        '.SH DESCRIPTION\n'
        'Opens the LOUKSNA Zona Directiva desktop application.\n'
        'GitHub connectivity is explicit and credentials use Secret Service.\n'
        '.SH SECURITY\n'
        'No secret is embedded in the Debian package.\n'
        'Network state requires a successful API response.\n'
    ).encode("utf-8")
    with gzip.GzipFile(filename="",mode="wb",fileobj=(man/"louksna-zona-directiva.1.gz").open("wb"),mtime=0) as gz:
        gz.write(man_text)

    md5_lines=[]
    for p in sorted(stage.rglob("*")):
        if not p.is_file():
            continue
        rel=p.relative_to(stage).as_posix()
        if rel.startswith("DEBIAN/"):
            continue
        h=hashlib.md5(p.read_bytes()).hexdigest()
        md5_lines.append(f"{h}  {rel}")
    (stage/"DEBIAN"/"md5sums").write_text("\n".join(md5_lines)+"\n",encoding="utf-8")

    rebuilt=Path(td)/deb.name
    subprocess.run(["dpkg-deb","--build","--root-owner-group",str(stage),str(rebuilt)],check=True)
    shutil.copy2(rebuilt,deb)

print("TELEMETRY V03_DEB_SANITIZE=PASS")
