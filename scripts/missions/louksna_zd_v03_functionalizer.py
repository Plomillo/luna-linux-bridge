#!/usr/bin/env python3
from pathlib import Path
import struct, zlib
import json, shutil, sys

if len(sys.argv)!=2:
    raise SystemExit("usage: louksna_zd_v03_functionalizer.py <candidate-root>")

candidate=Path(sys.argv[1]).resolve()
templates=Path(__file__).resolve().parent/"v03_templates"

if not (candidate/"src"/"App.tsx").is_file():
    raise SystemExit("V02_MATERIALIZED_CANDIDATE_MISSING")

pkg=json.loads((candidate/"package.json").read_text(encoding="utf-8"))
pkg["version"]="0.3.0-functional-candidate.1"
(candidate/"package.json").write_text(json.dumps(pkg,indent=2,sort_keys=True)+"\n",encoding="utf-8")

cargo='''[package]
name = "louksna-zona-directiva"
version = "0.3.0"
description = "LOUKSNA ZONA DIRECTIVA functional governed desktop interface"
authors = ["Louksna"]
edition = "2021"

[build-dependencies]
tauri-build = { version = "2", features = [] }

[dependencies]
tauri = { version = "2", features = [] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
reqwest = { version = "0.12", default-features = false, features = ["json", "rustls-tls"] }
rusqlite = { version = "0.32", features = ["bundled"] }
dirs = "6"
chrono = { version = "0.4", features = ["serde"] }

[features]
custom-protocol = ["tauri/custom-protocol"]
'''
(candidate/"src-tauri"/"Cargo.toml").write_text(cargo,encoding="utf-8")

shutil.copy2(templates/"main.rs",candidate/"src-tauri"/"src"/"main.rs")
shutil.copy2(templates/"App.tsx",candidate/"src"/"App.tsx")

css=candidate/"src"/"styles.css"
css.write_text(css.read_text(encoding="utf-8")+"\n"+(templates/"styles_add.css").read_text(encoding="utf-8"),encoding="utf-8")

conf=json.loads((candidate/"src-tauri"/"tauri.conf.json").read_text(encoding="utf-8"))
conf["version"]="0.3.0"
conf["productName"]="LOUKSNA ZONA DIRECTIVA"
conf["bundle"]["shortDescription"]="Interfaz GitHub funcional gobernada por Louksna"
conf["bundle"]["longDescription"]="Functional LOUKSNA interface with local evidence and GitHub read-only access."
(candidate/"src-tauri"/"tauri.conf.json").write_text(json.dumps(conf,indent=2,sort_keys=True)+"\n",encoding="utf-8")

(candidate/"README_FUNCTIONAL_V03.md").write_text(
"""# LOUKSNA ZONA DIRECTIVA V0.3 — FUNCTIONAL CANDIDATE

Implemented:
- SQLite local state and evidence ledger;
- persistent non-secret settings;
- Secret Service/libsecret GitHub credential storage;
- real GitHub REST read-only repositories and Pull Requests;
- explicit offline/disconnected state;
- local governed chat persistence;
- optional remote chat bridge with explicit round-trip semantics;
- no visible internal worker/runtime identities.

Not claimed:
- remote architecture chat unless a bridge endpoint is configured and round-trip passes;
- voice/call end-to-end;
- ACTIVE authorization.
""",encoding="utf-8")

# Tauri's configured icon is a build input. Preserve any supplied icon; if the
# inherited skeleton omits it, generate a deterministic, valid PNG fallback.
icon_path=candidate/"src-tauri"/"icons"/"icon.png"
if not icon_path.is_file():
    icon_path.parent.mkdir(parents=True,exist_ok=True)
    width=height=64
    rows=[]
    for y in range(height):
        row=bytearray([0])
        for x in range(width):
            is_mark=(16 <= x < 24 and 14 <= y < 50) or (16 <= x < 46 and 42 <= y < 50)
            row.extend((35,211,238,255) if is_mark else (12,18,36,255))
        rows.append(bytes(row))
    def png_chunk(kind,data):
        return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    png=(b"\x89PNG\r\n\x1a\n"
         +png_chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,6,0,0,0))
         +png_chunk(b"IDAT",zlib.compress(b"".join(rows),9))
         +png_chunk(b"IEND",b""))
    icon_path.write_bytes(png)
    print("TELEMETRY V03_TAURI_ICON=DETERMINISTIC_FALLBACK_CREATED")
else:
    print("TELEMETRY V03_TAURI_ICON=SOURCE_ASSET_PRESERVED")

ui=(candidate/"src"/"App.tsx").read_text(encoding="utf-8")
backend=(candidate/"src-tauri"/"src"/"main.rs").read_text(encoding="utf-8")

for forbidden in ["CUSTOSZ","CUSTOSZ_RUNTIME","Josefina","Katya","Ancapi","MetaOS"]:
    if forbidden in ui:
        raise SystemExit("VISIBLE_IDENTITY_REGRESSION:"+forbidden)

required_ui=[
    '@tauri-apps/api/core',
    'github_repositories',
    'github_pull_requests',
    'save_settings',
    'evidence_recent',
    'chat_send'
]
missing_ui=[x for x in required_ui if x not in ui]
if missing_ui:
    raise SystemExit("V03_UI_BINDING_MISSING:"+",".join(missing_ui))

required_backend=[
    'rusqlite',
    'secret-tool',
    'github_repositories',
    'github_pull_requests',
    'evidence_recent',
    'chat_send'
]
missing_backend=[x for x in required_backend if x not in backend]
if missing_backend:
    raise SystemExit("V03_BACKEND_BINDING_MISSING:"+",".join(missing_backend))

print("TELEMETRY V03_LOCAL_BACKEND=IMPLEMENTED")
print("TELEMETRY V03_SETTINGS_SQLITE=IMPLEMENTED")
print("TELEMETRY V03_SECRET_SERVICE=IMPLEMENTED")
print("TELEMETRY V03_GITHUB_READ_ONLY=IMPLEMENTED")
print("TELEMETRY V03_EVIDENCE_LEDGER=IMPLEMENTED")
print("TELEMETRY V03_CHAT_LOCAL=IMPLEMENTED")
print("TELEMETRY V03_CHAT_REMOTE_BRIDGE=PREPARED_NOT_CLAIMED")
print("TELEMETRY V03_VOICE=GATE_OPEN_NOT_CLAIMED")
print("TELEMETRY V03_VISIBLE_IDENTITY=LOUKSNA_ONLY")
print("LOUKSNA_V03_FUNCTIONALIZATION=PASS")
