#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone

ROOT_LINK = "https://www.dropbox.com/scl/fo/0dhs5jhwksqtmwl26vusi/AIIzeblluaJfhuXh9EnP-10?rlkey=p712fwlkbwn9g0dtybu2sf159&st=3igdng0g&dl=0"
ROOT = pathlib.Path(os.environ["STATE_ROOT"])
EVID = ROOT / "evidence"
DL = ROOT / "browser-downloads"
PAYLOAD = ROOT / "payload"
for p in (EVID, DL, PAYLOAD):
    p.mkdir(parents=True, exist_ok=True)

MAX_DEPTH = 16
MAX_NODES = 50000

def utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def atomic_json(path: pathlib.Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def clean_label(text: str, fallback: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", "_", (text or "").strip())
    text = re.sub(r"\s+", " ", text).strip(" .")
    return (text[:120] or fallback)

def link_key(url: str) -> str:
    u = urllib.parse.urlsplit(url)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(u.query, keep_blank_values=True) if k in {"rlkey", "st"}]
    raw = urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, urllib.parse.urlencode(q), ""))
    return hashlib.sha256(raw.encode()).hexdigest()

def sanitize_url(url: str) -> dict:
    u = urllib.parse.urlsplit(url)
    return {
        "scheme": u.scheme,
        "host": u.hostname,
        "path": u.path,
        "query_keys": sorted({k for k, _ in urllib.parse.parse_qsl(u.query, keep_blank_values=True)}),
        "identity_sha256": link_key(url),
    }

def with_dl(url: str, value: str) -> str:
    u = urllib.parse.urlsplit(url)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(u.query, keep_blank_values=True) if k != "dl"]
    q.append(("dl", value))
    return urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, urllib.parse.urlencode(q), u.fragment))

def record_event(kind: str, **kwargs) -> None:
    p = EVID / "EVENTS.ndjson"
    row = {"utc": utc(), "kind": kind, **kwargs}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())

def dismiss_overlays(page) -> None:
    for txt in ("Accept", "Accept all", "Reject all", "Aceptar", "Aceptar todas", "Rechazar todas"):
        try:
            loc = page.get_by_text(txt, exact=True)
            if loc.count() and loc.first.is_visible():
                loc.first.click(timeout=1500)
                break
        except Exception:
            pass
    for pat in (
        re.compile("close", re.I),
        re.compile("not now", re.I),
        re.compile("cerrar", re.I),
        re.compile("ahora no", re.I),
    ):
        try:
            loc = page.get_by_role("button", name=pat)
            if loc.count() and loc.first.is_visible():
                loc.first.click(timeout=1200)
        except Exception:
            pass

def inventory_children(page, url: str) -> list[dict]:
    page.goto(url, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(12000)
    dismiss_overlays(page)
    page.wait_for_timeout(1000)
    current_path = urllib.parse.urlsplit(url).path
    seen: dict[str, dict] = {}
    stable = 0
    prior = -1
    for _ in range(180):
        anchors = page.locator("a[href]")
        count = anchors.count()
        for i in range(count):
            try:
                a = anchors.nth(i)
                href = a.get_attribute("href") or ""
                absolute = urllib.parse.urljoin(page.url, href)
                u = urllib.parse.urlsplit(absolute)
                if u.hostname != "www.dropbox.com":
                    continue
                typ = None
                if "/scl/fi/" in u.path:
                    typ = "file"
                elif "/scl/fo/" in u.path and u.path != current_path:
                    typ = "folder"
                if typ is None:
                    continue
                text = (a.inner_text(timeout=300) or "").strip()
                key = link_key(absolute)
                seen[key] = {
                    "kind": typ,
                    "url": absolute,
                    "label": clean_label(text, typ + "-" + key[:10]),
                    "key": key,
                }
            except Exception:
                pass
        if len(seen) == prior:
            stable += 1
        else:
            stable = 0
            prior = len(seen)
        try:
            page.mouse.wheel(0, 4500)
            page.wait_for_timeout(700)
        except Exception:
            pass
        if stable >= 8:
            break
    rows = sorted(seen.values(), key=lambda x: (x["kind"], x["label"].casefold(), x["key"]))
    record_event("CHILD_INVENTORY", parent=sanitize_url(url), count=len(rows),
                 files=sum(x["kind"] == "file" for x in rows),
                 folders=sum(x["kind"] == "folder" for x in rows))
    return rows

def write_download_event(kind: str, source_url: str, label: str, suggested: str | None = None) -> None:
    marker = {
        "schema": "LOUKSNA_DROPBOX_GITHUB_PARTITION_DOWNLOAD_EVENT/1.0",
        "status": "PASS",
        "provider": "DROPBOX_CONNECTED_PLUGIN",
        "execution_plane": "GITHUB_HOSTED_UBUNTU_24_04",
        "source_object_identified": True,
        "source_kind": kind,
        "source_identity": sanitize_url(source_url),
        "label": label,
        "suggested_filename": suggested,
        "download_event_observed": True,
        "local_pc_data_plane": False,
        "self_hosted_runner_data_plane": False,
        "observed_at_utc": utc(),
    }
    first = EVID / "FIRST_DOWNLOAD_EVENT.json"
    if not first.exists():
        atomic_json(first, marker)
    atomic_json(EVID / "CURRENT_DOWNLOAD_EVENT.json", marker)
    record_event("DOWNLOAD_EVENT", kind=kind, label=label, source=sanitize_url(source_url), suggested_filename=suggested)

def validate_zip(path: pathlib.Path) -> tuple[int, str]:
    if not zipfile.is_zipfile(path):
        raise RuntimeError("PARTITION_NOT_ZIP:" + path.name)
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError("PARTITION_ZIP_CRC_FAIL:" + bad)
        count = len(z.infolist())
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return count, h.hexdigest()

def download_file_link(url: str, label: str, ordinal: int) -> dict:
    target_url = with_dl(url, "1")
    req = urllib.request.Request(target_url, headers={"User-Agent": "LOUKSNA-GitHub-Cloud-Partitioned/1.0"})
    key = link_key(url)
    part = PAYLOAD / f"{ordinal:06d}_file_{key[:12]}.part"
    final = PAYLOAD / f"{ordinal:06d}_file_{key[:12]}.bin"
    with urllib.request.urlopen(req, timeout=120) as resp:
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "text/html" in ctype:
            raise RuntimeError("FILE_LINK_RETURNED_HTML:" + key)
        first = resp.read(1024 * 1024)
        if not first:
            raise RuntimeError("FILE_LINK_EMPTY:" + key)
        with part.open("wb") as f:
            f.write(first)
            f.flush()
            os.fsync(f.fileno())
            write_download_event("file", url, label, final.name)
            while True:
                chunk = resp.read(8 * 1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
        os.replace(part, final)
    h = hashlib.sha256()
    with final.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return {
        "kind": "file",
        "label": label,
        "source_identity_sha256": key,
        "payload_name": final.name,
        "bytes": final.stat().st_size,
        "sha256": h.hexdigest(),
    }

def attempt_folder_download(page, url: str, label: str, ordinal: int):
    page.goto(url, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(2500)
    dismiss_overlays(page)

    primary = page.locator('button[data-testid="action-bar-download-button"]')
    primary.first.wait_for(state="visible", timeout=60000)
    primary.first.click(timeout=10000)

    continuation = None
    for selector in (
        'button:has-text("Or continue with download only")',
        'button:has-text("Continue with download only")',
        'button:has-text("continuar solo con la descarga")',
    ):
        loc = page.locator(selector)
        try:
            loc.first.wait_for(state="visible", timeout=20000)
            continuation = loc.first
            break
        except Exception:
            pass
    if continuation is None:
        raise RuntimeError("FOLDER_DOWNLOAD_CONTINUATION_NOT_FOUND:" + link_key(url))

    state = {"download": None, "generate": None}

    def on_download(download):
        if state["download"] is None:
            state["download"] = download
            write_download_event("folder", url, label, download.suggested_filename)

    def on_response(resp):
        try:
            if "/2/sharing_receiving/generate_download_url" not in resp.url:
                return
            body = None
            try:
                body = resp.json()
            except Exception:
                pass
            state["generate"] = {"status": resp.status, "body": body}
            atomic_json(EVID / "LAST_GENERATE_DOWNLOAD_URL.json", {
                "schema": "LOUKSNA_DROPBOX_GENERATE_DOWNLOAD_URL_RESULT/1.0",
                "status_code": resp.status,
                "source_identity_sha256": link_key(url),
                "body": body if resp.status >= 400 else None,
                "observed_at_utc": utc(),
            })
        except Exception:
            pass

    page.on("download", on_download)
    page.on("response", on_response)
    try:
        continuation.click(timeout=10000)
        deadline = time.time() + 190
        while time.time() < deadline:
            if state["download"] is not None:
                break
            gen = state["generate"]
            if gen and int(gen.get("status") or 0) >= 400:
                break
            page.wait_for_timeout(250)
    finally:
        try:
            page.remove_listener("download", on_download)
            page.remove_listener("response", on_response)
        except Exception:
            pass

    if state["download"] is not None:
        download = state["download"]
        key = link_key(url)
        final = PAYLOAD / f"{ordinal:06d}_folder_{key[:12]}.zip"
        download.save_as(str(final))
        failure = download.failure()
        if failure:
            raise RuntimeError("FOLDER_DOWNLOAD_FAILURE:" + str(failure))
        entries, sha = validate_zip(final)
        return {
            "action": "downloaded",
            "result": {
                "kind": "folder_zip",
                "label": label,
                "source_identity_sha256": key,
                "payload_name": final.name,
                "bytes": final.stat().st_size,
                "sha256": sha,
                "entry_count": entries,
            },
        }

    gen = state["generate"] or {}
    body = gen.get("body") if isinstance(gen, dict) else None
    msg = ""
    if isinstance(body, dict):
        um = body.get("user_message")
        if isinstance(um, dict):
            msg = str(um.get("text") or "")
        summary = str(body.get("error_summary") or "")
        tag = ""
        err = body.get("error")
        if isinstance(err, dict):
            tag = str(err.get(".tag") or err.get("tag") or "")
    else:
        summary = tag = ""
    normalized = (msg + " " + summary + " " + tag).lower()
    if int(gen.get("status") or 0) == 409 and "too many files" in normalized:
        record_event("PARTITION_REQUIRED", label=label, source=sanitize_url(url), reason="TOO_MANY_FILES")
        return {"action": "split"}
    raise RuntimeError("FOLDER_DOWNLOAD_NO_MATERIAL:" + json.dumps({
        "status": gen.get("status"),
        "error_summary": summary,
        "tag": tag,
        "message": msg,
        "source_identity_sha256": link_key(url),
    }, ensure_ascii=False, sort_keys=True))

def main() -> None:
    from playwright.sync_api import sync_playwright

    manifest = {
        "schema": "LOUKSNA_DROPBOX_GITHUB_PARTITIONED_MANIFEST/1.0",
        "status": "RUNNING",
        "authority": "Louksna.md",
        "source_root": sanitize_url(ROOT_LINK),
        "execution_plane": "GITHUB_HOSTED_UBUNTU_24_04",
        "local_pc_data_plane": False,
        "self_hosted_runner_data_plane": False,
        "desktop_commander": False,
        "started_at_utc": utc(),
        "completed": [],
        "split_folders": [],
    }
    atomic_json(EVID / "MANIFEST.json", manifest)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, downloads_path=str(DL))
        context = browser.new_context(accept_downloads=True, locale="en-US")
        page = context.new_page()

        root_children = inventory_children(page, ROOT_LINK)
        if not root_children:
            raise SystemExit("ROOT_CHILDREN_EMPTY")
        atomic_json(EVID / "ROOT_INVENTORY.json", {
            "schema": "LOUKSNA_DROPBOX_ROOT_PARTITION_INVENTORY/1.0",
            "status": "PASS",
            "count": len(root_children),
            "folders": sum(x["kind"] == "folder" for x in root_children),
            "files": sum(x["kind"] == "file" for x in root_children),
            "child_identity_sha256": [x["key"] for x in root_children],
            "observed_at_utc": utc(),
        })

        queue = [{"depth": 1, **x} for x in root_children]
        queued = {x["key"] for x in queue}
        completed_keys = set()
        ordinal = 0

        while queue:
            if len(queued) > MAX_NODES:
                raise RuntimeError("MAX_NODES_EXCEEDED")
            item = queue.pop(0)
            key = item["key"]
            if key in completed_keys:
                continue
            depth = int(item["depth"])
            if depth > MAX_DEPTH:
                raise RuntimeError("MAX_DEPTH_EXCEEDED:" + key)
            ordinal += 1
            atomic_json(EVID / "PROGRESS.json", {
                "schema": "LOUKSNA_DROPBOX_PARTITION_PROGRESS/1.0",
                "status": "RUNNING",
                "current": {"kind": item["kind"], "label": item["label"], "depth": depth, "identity_sha256": key},
                "completed_count": len(manifest["completed"]),
                "queue_remaining": len(queue),
                "seen_nodes": len(queued),
                "updated_at_utc": utc(),
            })

            if item["kind"] == "file":
                result = download_file_link(item["url"], item["label"], ordinal)
                manifest["completed"].append(result)
                completed_keys.add(key)
                atomic_json(EVID / "MANIFEST.json", manifest)
                continue

            attempt = attempt_folder_download(page, item["url"], item["label"], ordinal)
            if attempt["action"] == "downloaded":
                manifest["completed"].append(attempt["result"])
                completed_keys.add(key)
                atomic_json(EVID / "MANIFEST.json", manifest)
                continue

            if attempt["action"] == "split":
                children = inventory_children(page, item["url"])
                if not children:
                    raise RuntimeError("PARTITION_REQUIRED_BUT_CHILDREN_EMPTY:" + key)
                manifest["split_folders"].append({
                    "label": item["label"],
                    "source_identity_sha256": key,
                    "depth": depth,
                    "child_count": len(children),
                })
                for child in children:
                    if child["key"] not in queued and child["key"] not in completed_keys:
                        queue.append({"depth": depth + 1, **child})
                        queued.add(child["key"])
                completed_keys.add(key)
                atomic_json(EVID / "MANIFEST.json", manifest)
                continue

            raise RuntimeError("UNKNOWN_PARTITION_ACTION")

        browser.close()

    manifest["status"] = "PASS"
    manifest["completed_at_utc"] = utc()
    manifest["payload_count"] = len(manifest["completed"])
    manifest["payload_bytes"] = sum(int(x["bytes"]) for x in manifest["completed"])
    atomic_json(EVID / "MANIFEST.json", manifest)
    print(json.dumps({
        "PARTITIONED_ACQUISITION": "PASS",
        "payload_count": manifest["payload_count"],
        "payload_bytes": manifest["payload_bytes"],
        "split_folders": len(manifest["split_folders"]),
    }, sort_keys=True))

if __name__ == "__main__":
    main()
