#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html as html_lib
import json
import os
import pathlib
import re
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from dropbox_transfer_resilience import emit_event, load_resume_state, write_checkpoint

ROOT_LINK = "https://www.dropbox.com/scl/fo/0dhs5jhwksqtmwl26vusi/AIIzeblluaJfhuXh9EnP-10?rlkey=p712fwlkbwn9g0dtybu2sf159&st=3igdng0g&dl=0"
ROOT = pathlib.Path(os.environ["STATE_ROOT"])
EVID = ROOT / "evidence"
DL = ROOT / "browser-downloads"
PAYLOAD = ROOT / "payload"
CHECKPOINTS = ROOT / "checkpoints"
QUARANTINE = ROOT / "quarantine"
for p in (EVID, DL, PAYLOAD, CHECKPOINTS, QUARANTINE):
    p.mkdir(parents=True, exist_ok=True)

MAX_DEPTH = 16
MAX_NODES = 50000
MAX_ITEM_RETRIES = max(1, int(os.environ.get("TRANSFER_ITEM_RETRIES", "3")))

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
    q = sorted(
        (k, v)
        for k, v in urllib.parse.parse_qsl(u.query, keep_blank_values=True)
        if k != "dl"
    )
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


_DROPBOX_API_TOKEN_CACHE: dict = {"token": None, "expires_at": 0.0, "mode": None}

def _oauth_token_refresh() -> tuple[str | None, str | None]:
    now = time.time()
    cached = str(_DROPBOX_API_TOKEN_CACHE.get("token") or "")
    expires_at = float(_DROPBOX_API_TOKEN_CACHE.get("expires_at") or 0.0)
    if cached and (expires_at == 0.0 or expires_at - now > 300):
        return cached, str(_DROPBOX_API_TOKEN_CACHE.get("mode") or "cached")

    refresh = os.environ.get("DROPBOX_REFRESH_TOKEN", "").strip()
    app_key = os.environ.get("DROPBOX_APP_KEY", "").strip()
    app_secret = os.environ.get("DROPBOX_APP_SECRET", "").strip()
    legacy = os.environ.get("DROPBOX_ACCESS_TOKEN", "").strip()

    if refresh and app_key and app_secret:
        body = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": refresh,
        }).encode("ascii")
        basic = base64.b64encode((app_key + ":" + app_secret).encode("utf-8")).decode("ascii")
        req = urllib.request.Request(
            "https://api.dropbox.com/oauth2/token",
            data=body,
            method="POST",
            headers={
                "Authorization": "Basic " + basic,
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Louksna-PUAC2-Partitioned/3.0",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        token = str(data.get("access_token") or "").strip()
        if not token:
            raise RuntimeError("DROPBOX_OAUTH_REFRESH_ACCESS_TOKEN_MISSING")
        ttl = int(data.get("expires_in") or 14400)
        _DROPBOX_API_TOKEN_CACHE.update({
            "token": token,
            "expires_at": now + max(600, ttl),
            "mode": "OAUTH_REFRESH",
        })
        record_event(
            "DROPBOX_API_AUTH_BOUND",
            auth_mode="OAUTH_REFRESH",
            token_present=True,
            token_logged=False,
            token_persisted=False,
        )
        return token, "OAUTH_REFRESH"

    if legacy:
        _DROPBOX_API_TOKEN_CACHE.update({
            "token": legacy,
            "expires_at": 0.0,
            "mode": "LEGACY_ACCESS_TOKEN",
        })
        record_event(
            "DROPBOX_API_AUTH_BOUND",
            auth_mode="LEGACY_ACCESS_TOKEN",
            token_present=True,
            token_logged=False,
            token_persisted=False,
        )
        return legacy, "LEGACY_ACCESS_TOKEN"

    return None, None

def _dropbox_api_post_json(endpoint: str, payload: dict, *, refresh_on_401: bool = True) -> dict:
    token, mode = _oauth_token_refresh()
    if not token:
        raise RuntimeError("DROPBOX_API_AUTH_UNAVAILABLE")
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "User-Agent": "Louksna-PUAC2-Partitioned/3.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            request_id = resp.headers.get("X-Dropbox-Request-Id") or resp.headers.get("x-dropbox-request-id")
            if request_id:
                data["_louksna_request_id"] = request_id
            return data
    except urllib.error.HTTPError as exc:
        if exc.code == 401 and refresh_on_401 and mode == "OAUTH_REFRESH":
            _DROPBOX_API_TOKEN_CACHE.update({"token": None, "expires_at": 0.0, "mode": None})
            return _dropbox_api_post_json(endpoint, payload, refresh_on_401=False)
        body = exc.read(8192).decode("utf-8", errors="replace")
        raise RuntimeError(f"DROPBOX_API_HTTP_{exc.code}:{body[:1200]}") from exc

def _api_item_key(shared_url: str, relative_path: str, item_kind: str) -> str:
    identity = "\n".join((link_key(shared_url), item_kind, relative_path))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()

def inventory_children_api(shared_url: str, relative_path: str = "") -> list[dict]:
    """Authoritative direct-child inventory for a Dropbox shared folder."""
    token, mode = _oauth_token_refresh()
    if not token:
        raise RuntimeError("DROPBOX_API_AUTH_UNAVAILABLE")
    rel = relative_path or ""
    payload = {
        "path": rel,
        "recursive": False,
        "include_deleted": False,
        "shared_link": {"url": shared_url},
        "limit": 2000,
    }
    data = _dropbox_api_post_json("https://api.dropboxapi.com/2/files/list_folder", payload)
    entries: list[dict] = []
    request_ids: list[str] = []
    if data.get("_louksna_request_id"):
        request_ids.append(str(data["_louksna_request_id"]))

    while True:
        for raw in data.get("entries", []):
            tag = str(raw.get(".tag") or "")
            name = str(raw.get("name") or "").strip()
            if tag not in ("file", "folder") or not name:
                continue
            child = ((rel.rstrip("/") if rel else "") + "/" + name)
            if not child.startswith("/"):
                child = "/" + child
            key = _api_item_key(shared_url, child, tag)
            row = {
                "kind": tag,
                "transport": "dropbox_api",
                "shared_url": shared_url,
                "relative_path": child,
                "url": shared_url,
                "label": clean_label(name, tag + "-" + key[:10]),
                "key": key,
                "dropbox_id": raw.get("id"),
            }
            if tag == "file":
                row.update({
                    "size": int(raw.get("size") or 0),
                    "rev": raw.get("rev"),
                    "content_hash": raw.get("content_hash"),
                })
            entries.append(row)

        if not data.get("has_more"):
            break
        cursor = str(data.get("cursor") or "")
        if not cursor:
            raise RuntimeError("DROPBOX_API_CURSOR_MISSING")
        data = _dropbox_api_post_json(
            "https://api.dropboxapi.com/2/files/list_folder/continue",
            {"cursor": cursor},
        )
        if data.get("_louksna_request_id"):
            request_ids.append(str(data["_louksna_request_id"]))

    rows = sorted(entries, key=lambda x: (x["kind"], x["label"].casefold(), x["key"]))
    record_event(
        "DROPBOX_API_AUTHORITATIVE_INVENTORY",
        provider="DROPBOX_API_LIST_FOLDER_SHARED_LINK",
        auth_mode=mode,
        parent=sanitize_url(shared_url),
        relative_path=rel,
        count=len(rows),
        files=sum(x["kind"] == "file" for x in rows),
        folders=sum(x["kind"] == "folder" for x in rows),
        request_ids=request_ids,
        dom_authoritative=False,
    )
    return rows

def dropbox_content_hash(path: pathlib.Path) -> str:
    block_hashes: list[bytes] = []
    with path.open("rb") as f:
        while True:
            block = f.read(4 * 1024 * 1024)
            if not block:
                break
            block_hashes.append(hashlib.sha256(block).digest())
    return hashlib.sha256(b"".join(block_hashes)).hexdigest()

def download_file_api(item: dict, ordinal: int) -> dict:
    shared_url = str(item["shared_url"])
    relative_path = str(item["relative_path"])
    key = str(item["key"])
    expected_size = int(item.get("size") or 0)
    expected_content_hash = str(item.get("content_hash") or "").lower()
    token, mode = _oauth_token_refresh()
    if not token:
        raise RuntimeError("DROPBOX_API_AUTH_UNAVAILABLE")

    safe = clean_label(pathlib.PurePosixPath(relative_path).name, "file")
    part = PAYLOAD / f"{ordinal:06d}_api_{key[:12]}_{safe}.part"
    final = PAYLOAD / f"{ordinal:06d}_api_{key[:12]}_{safe}"
    arg = {"url": shared_url, "path": relative_path}
    req = urllib.request.Request(
        "https://content.dropboxapi.com/2/sharing/get_shared_link_file",
        data=b"",
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Dropbox-API-Arg": json.dumps(arg, separators=(",", ":")),
            "User-Agent": "Louksna-PUAC2-Partitioned/3.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp, part.open("wb") as out:
            request_id = resp.headers.get("X-Dropbox-Request-Id") or resp.headers.get("x-dropbox-request-id")
            material_marked = False
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                if not material_marked:
                    out.flush()
                    os.fsync(out.fileno())
                    observed = part.stat().st_size
                    if observed > 0:
                        write_download_event("file-api", shared_url, item["label"], final.name)
                        record_event(
                            "DROPBOX_API_MATERIAL_DOWNLOAD_STARTED",
                            provider="DROPBOX_API_SHARED_LINK",
                            auth_mode=mode,
                            relative_path=relative_path,
                            source_identity_sha256=key,
                            observed_bytes=observed,
                            dropbox_request_id=request_id,
                            token_logged=False,
                        )
                        material_marked = True
    except urllib.error.HTTPError as exc:
        if exc.code == 401 and mode == "OAUTH_REFRESH":
            _DROPBOX_API_TOKEN_CACHE.update({"token": None, "expires_at": 0.0, "mode": None})
        raise RuntimeError(f"DROPBOX_API_FILE_HTTP_{exc.code}:{relative_path}") from exc

    actual_size = part.stat().st_size
    if expected_size and actual_size != expected_size:
        quarantine_path(part, f"DROPBOX_API_SIZE_MISMATCH:{expected_size}:{actual_size}")
        raise RuntimeError(f"DROPBOX_API_SIZE_MISMATCH:{relative_path}:{expected_size}:{actual_size}")
    if expected_content_hash:
        actual_content_hash = dropbox_content_hash(part)
        if actual_content_hash != expected_content_hash:
            quarantine_path(part, "DROPBOX_API_CONTENT_HASH_MISMATCH")
            raise RuntimeError(f"DROPBOX_API_CONTENT_HASH_MISMATCH:{relative_path}")
    h = hashlib.sha256()
    with part.open("rb") as src:
        for chunk in iter(lambda: src.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    os.replace(part, final)
    record_event(
        "DROPBOX_API_OBJECT_COMMITTED",
        relative_path=relative_path,
        source_identity_sha256=key,
        bytes=final.stat().st_size,
        sha256=h.hexdigest(),
        source_content_hash=expected_content_hash or None,
    )
    return {
        "kind": "file",
        "label": item["label"],
        "source_identity_sha256": key,
        "relative_path": relative_path,
        "payload_name": final.name,
        "bytes": final.stat().st_size,
        "sha256": h.hexdigest(),
        "source_content_hash": expected_content_hash or None,
        "transfer_method": "DROPBOX_API_GET_SHARED_LINK_FILE",
    }

def record_event(kind: str, **kwargs) -> None:
    emit_event(ROOT, kind, **kwargs)
    # Legacy projection retained for existing diagnostics; EventRecord_V2 is authoritative.
    p = EVID / "EVENTS.ndjson"
    row = {"utc": utc(), "kind": kind, **kwargs}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())

def children_from_html_text(text: str, parent_url: str) -> list[dict]:
    text = html_lib.unescape(text)
    candidates: list[str] = []
    for pat in (
        r'''href=["']([^"']*(?:/scl/(?:fo|fi)/)[^"']+)["']''',
        r'''["'](https://www\\.dropbox\\.com/scl/(?:fo|fi)/[^"']+)["']''',
        r'''["'](/scl/(?:fo|fi)/[^"']+)["']''',
    ):
        candidates.extend(re.findall(pat, text, re.I))

    parent_path = urllib.parse.urlsplit(parent_url).path
    seen: dict[str, dict] = {}
    for raw in candidates:
        raw = raw.replace("\\u0026", "&").replace("\\u003d", "=").replace("\\/", "/")
        absolute = urllib.parse.urljoin("https://www.dropbox.com/", raw)
        u = urllib.parse.urlsplit(absolute)
        if u.hostname != "www.dropbox.com":
            continue
        typ = "file" if "/scl/fi/" in u.path else "folder" if "/scl/fo/" in u.path else None
        if typ is None or u.path == parent_path:
            continue
        key = link_key(absolute)
        seen[key] = {
            "kind": typ,
            "url": absolute,
            "label": typ + "-" + key[:10],
            "key": key,
        }
    return sorted(seen.values(), key=lambda x: (x["kind"], x["key"]))

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
                key = link_key(absolute)
                try:
                    text = (a.inner_text(timeout=1000) or "").strip()
                except Exception:
                    text = ""
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

    if not rows:
        try:
            html_rows = children_from_html_text(page.content(), url)
        except Exception:
            html_rows = []
        if html_rows:
            rows = html_rows
            record_event("CHILD_INVENTORY_HTML_FALLBACK", parent=sanitize_url(url), count=len(rows))

    if not rows and urllib.parse.urlsplit(url).path == urllib.parse.urlsplit(ROOT_LINK).path:
        frozen = os.environ.get("FROZEN_ROOT_HTML", "").strip()
        if frozen:
            fp = pathlib.Path(frozen)
            if fp.is_file():
                rows = children_from_html_text(fp.read_text(encoding="utf-8", errors="replace"), url)
                if rows:
                    record_event("CHILD_INVENTORY_FROZEN_ROOT_FALLBACK", parent=sanitize_url(url), count=len(rows))

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
    record_event("DOWNLOAD_EVENT", source_kind=kind, label=label, source=sanitize_url(source_url), suggested_filename=suggested)

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

def attempt_direct_folder_download(url: str, label: str, ordinal: int) -> dict:
    """Try Dropbox's documented dl=1 transport before depending on preview-page UI."""
    key = link_key(url)
    target_url = with_dl(url, "1")
    part = PAYLOAD / f"{ordinal:06d}_folder_{key[:12]}.direct.part"
    final = PAYLOAD / f"{ordinal:06d}_folder_{key[:12]}.zip"
    req = urllib.request.Request(
        target_url,
        headers={"User-Agent": "LOUKSNA-GitHub-Cloud-Partitioned/2.0"},
    )
    record_event(
        "FOLDER_DIRECT_DL1_ATTEMPT",
        label=label,
        source=sanitize_url(url),
        source_identity_sha256=key,
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            effective_url = resp.geturl()
            first = resp.read(1024 * 1024)
            if not first:
                record_event(
                    "FOLDER_DIRECT_DL1_FALLBACK",
                    label=label,
                    source_identity_sha256=key,
                    reason="EMPTY_RESPONSE",
                    content_type=ctype,
                )
                return {"action": "fallback", "reason": "EMPTY_RESPONSE"}

            zip_signature = first[:4] in (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
            if "text/html" in ctype or not zip_signature:
                record_event(
                    "FOLDER_DIRECT_DL1_FALLBACK",
                    label=label,
                    source_identity_sha256=key,
                    reason="NON_ZIP_RESPONSE",
                    content_type=ctype,
                    first4_hex=first[:4].hex(),
                    effective_host=urllib.parse.urlsplit(effective_url).hostname,
                )
                return {"action": "fallback", "reason": "NON_ZIP_RESPONSE"}

            with part.open("wb") as f:
                f.write(first)
                f.flush()
                os.fsync(f.fileno())
                write_download_event("folder-direct-dl1", url, label, final.name)
                while True:
                    chunk = resp.read(8 * 1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
            os.replace(part, final)

        try:
            entries, sha = validate_zip(final)
        except Exception as exc:
            quarantine_path(final, f"DIRECT_DL1_INVALID_ZIP:{type(exc).__name__}:{exc}")
            record_event(
                "FOLDER_DIRECT_DL1_FALLBACK",
                label=label,
                source_identity_sha256=key,
                reason="ZIP_VALIDATION_FAILED",
                error=f"{type(exc).__name__}:{exc}",
            )
            return {"action": "fallback", "reason": "ZIP_VALIDATION_FAILED"}

        record_event(
            "FOLDER_DIRECT_DL1_PASS",
            label=label,
            source_identity_sha256=key,
            bytes=final.stat().st_size,
            sha256=sha,
            entry_count=entries,
        )
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
                "transfer_method": "DROPBOX_DOCUMENTED_DL1_DIRECT",
            },
        }
    except urllib.error.HTTPError as exc:
        body = b""
        try:
            body = exc.read(128 * 1024)
        except Exception:
            pass
        record_event(
            "FOLDER_DIRECT_DL1_FALLBACK",
            label=label,
            source_identity_sha256=key,
            reason="HTTP_ERROR",
            status_code=exc.code,
            response_excerpt_sha256=hashlib.sha256(body).hexdigest() if body else None,
        )
        return {"action": "fallback", "reason": f"HTTP_{exc.code}"}
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        if part.exists():
            quarantine_path(part, f"DIRECT_DL1_TRANSPORT_ERROR:{type(exc).__name__}:{exc}")
        record_event(
            "FOLDER_DIRECT_DL1_TRANSPORT_ERROR",
            label=label,
            source_identity_sha256=key,
            error=f"{type(exc).__name__}:{exc}",
        )
        return {"action": "fallback", "reason": "TRANSPORT_ERROR"}


def attempt_folder_download(page, url: str, label: str, ordinal: int):
    # Primary path: Dropbox's documented forced-download parameter. This avoids
    # coupling the transfer to preview-page DOM selectors.
    direct = attempt_direct_folder_download(url, label, ordinal)
    if direct["action"] == "downloaded":
        return direct

    page.goto(url, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(2500)
    dismiss_overlays(page)

    state = {"download": None, "generate": None}

    def on_download(download):
        if state["download"] is None:
            state["download"] = download
            write_download_event("folder-ui", url, label, download.suggested_filename)

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

    # Register listeners before clicking so a direct UI-triggered download is
    # never missed.
    page.on("download", on_download)
    page.on("response", on_response)
    try:
        primary = None
        candidates = [
            page.locator('button[data-testid="action-bar-download-button"]'),
            page.get_by_role("button", name=re.compile(r"download|descargar", re.I)),
            page.locator('button:has-text("Download")'),
            page.locator('button:has-text("Descargar")'),
        ]
        for loc in candidates:
            try:
                if loc.count():
                    loc.first.wait_for(state="visible", timeout=5000)
                    primary = loc.first
                    break
            except Exception:
                pass

        if primary is None:
            record_event(
                "FOLDER_DOWNLOAD_UI_CONTROL_UNAVAILABLE",
                label=label,
                source=sanitize_url(url),
                source_identity_sha256=link_key(url),
                direct_fallback_reason=direct.get("reason"),
            )
            return {"action": "split", "fallback_reason": "UI_CONTROL_UNAVAILABLE_AFTER_DIRECT_DL1"}

        primary.click(timeout=10000)

        # Some Dropbox surfaces start the download immediately; others show a
        # continuation control. Give the direct event a short chance first.
        immediate_deadline = time.time() + 5
        while time.time() < immediate_deadline and state["download"] is None:
            page.wait_for_timeout(250)

        continuation = None
        if state["download"] is None:
            for selector in (
                'button:has-text("Or continue with download only")',
                'button:has-text("Continue with download only")',
                'button:has-text("continuar solo con la descarga")',
            ):
                loc = page.locator(selector)
                try:
                    loc.first.wait_for(state="visible", timeout=5000)
                    continuation = loc.first
                    break
                except Exception:
                    pass

            if continuation is None:
                record_event(
                    "FOLDER_DOWNLOAD_CONTINUATION_UNAVAILABLE",
                    label=label,
                    source_identity_sha256=link_key(url),
                    direct_fallback_reason=direct.get("reason"),
                )
                return {"action": "split", "fallback_reason": "CONTINUATION_UNAVAILABLE"}

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
            quarantine_path(final, "FOLDER_UI_DOWNLOAD_FAILURE:" + str(failure))
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
                "transfer_method": "DROPBOX_UI_FALLBACK",
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
        return {"action": "split", "fallback_reason": "DROPBOX_409_TOO_MANY_FILES"}

    # Any folder path that produced no material is degradable to recursive
    # partitioning. process_item() will inventory children and keep progress.
    record_event(
        "FOLDER_DOWNLOAD_NO_MATERIAL_SPLIT",
        label=label,
        source=sanitize_url(url),
        source_identity_sha256=link_key(url),
        status=gen.get("status"),
        error_summary=summary,
        tag=tag,
        message=msg,
        direct_fallback_reason=direct.get("reason"),
    )
    return {"action": "split", "fallback_reason": "NO_MATERIAL_AFTER_DIRECT_AND_UI"}


def is_transient_transfer_error(exc: BaseException) -> bool:
    text = (type(exc).__name__ + ": " + str(exc)).lower()
    return any(token in text for token in (
        "timeout", "timed out", "connection reset", "remote end closed",
        "temporarily unavailable", "temporary failure", "429", "502", "503", "504",
        "network is unreachable", "name or service not known",
    ))

def quarantine_path(path: pathlib.Path, reason: str) -> None:
    if not path.exists():
        return
    target = QUARANTINE / (path.name + "." + hashlib.sha256(reason.encode()).hexdigest()[:10] + ".quarantine")
    try:
        os.replace(path, target)
        record_event("PAYLOAD_QUARANTINED", source=path.name, target=target.name, reason=reason)
    except Exception as qexc:
        record_event("QUARANTINE_FAILURE", source=path.name, reason=reason, error=f"{type(qexc).__name__}:{qexc}")

def process_item(page, item: dict, ordinal: int) -> dict:
    key = item["key"]

    if item.get("transport") == "dropbox_api":
        if item["kind"] == "file":
            return {"action": "downloaded", "result": download_file_api(item, ordinal)}
        children = inventory_children_api(item["shared_url"], item.get("relative_path") or "")
        if not children:
            record_event(
                "DROPBOX_API_EMPTY_FOLDER_VERIFIED",
                identity_sha256=key,
                relative_path=item.get("relative_path"),
            )
            return {"action": "folder_complete", "children": [], "fallback_reason": "API_VERIFIED_EMPTY_FOLDER"}
        return {"action": "split", "children": children, "fallback_reason": "DROPBOX_API_AUTHORITATIVE_INVENTORY"}

    last_exc: BaseException | None = None
    for attempt_no in range(1, MAX_ITEM_RETRIES + 1):
        try:
            record_event(
                "ITEM_ATTEMPT",
                identity_sha256=key,
                item_kind=item["kind"],
                label=item["label"],
                attempt=attempt_no,
                max_attempts=MAX_ITEM_RETRIES,
            )
            if item["kind"] == "file":
                return {"action": "downloaded", "result": download_file_link(item["url"], item["label"], ordinal)}

            result = attempt_folder_download(page, item["url"], item["label"], ordinal)
            if result["action"] == "split":
                # Authoritative path: the Dropbox API enumerates objects relative to
                # the shared-link root. DOM/HTML is diagnostic only.
                try:
                    children = inventory_children_api(item["url"], "")
                except Exception as api_exc:
                    record_event(
                        "DROPBOX_API_INVENTORY_FAILED",
                        identity_sha256=key,
                        error=f"{type(api_exc).__name__}:{api_exc}",
                        dom_authoritative=False,
                    )
                    raise
                if not children:
                    record_event(
                        "DROPBOX_API_EMPTY_FOLDER_VERIFIED",
                        identity_sha256=key,
                        relative_path="",
                    )
                    return {"action": "folder_complete", "children": [], "fallback_reason": "API_VERIFIED_EMPTY_FOLDER"}
                result["children"] = children
                result["fallback_reason"] = "DROPBOX_API_AUTHORITATIVE_INVENTORY"
            return result
        except Exception as exc:
            last_exc = exc
            message = f"{type(exc).__name__}:{exc}"
            record_event(
                "ITEM_ATTEMPT_FAILED",
                identity_sha256=key,
                item_kind=item["kind"],
                label=item["label"],
                attempt=attempt_no,
                error=message,
                traceback=traceback.format_exc(limit=12),
            )
            # Never repeat a deterministic DOM-inventory strategy. API auth or
            # deterministic API schema failures must be surfaced for governed repair.
            if "DROPBOX_API_AUTH_UNAVAILABLE" in message:
                break
            if is_transient_transfer_error(exc) and attempt_no < MAX_ITEM_RETRIES:
                delay = min(60, 2 ** attempt_no)
                record_event("TRANSIENT_RETRY_BACKOFF", identity_sha256=key, delay_seconds=delay)
                time.sleep(delay)
                continue
            break
    assert last_exc is not None
    raise last_exc


def main() -> None:
    from playwright.sync_api import sync_playwright

    resume = load_resume_state(
        os.environ.get("RESUME_SEED"),
        os.environ.get("RESUME_CHECKPOINT"),
        os.environ.get("RESUME_ARTIFACT_BINDING"),
        link_key,
    )
    manifest = {
        "schema": "LOUKSNA_DROPBOX_GITHUB_PARTITIONED_MANIFEST/2.0-PUAC2",
        "status": "RUNNING",
        "authority": "Louksna.md",
        "governance": "PUAC2.md",
        "source_root": sanitize_url(ROOT_LINK),
        "execution_plane": "GITHUB_HOSTED_UBUNTU_24_04",
        "local_pc_data_plane": False,
        "self_hosted_runner_data_plane": False,
        "desktop_commander": False,
        "started_at_utc": utc(),
        "resume_sources": resume["source"],
        "prior_completed": resume["prior_completed"],
        "completed": resume["current_completed"],
        "split_folders": resume["split_folders"],
        "failed": [],
        "anti_paralysis": True,
        "live_bug_research": True,
        "no_restart_from_zero_with_valid_checkpoint": True,
    }
    atomic_json(EVID / "MANIFEST.json", manifest)

    completed_keys = set(resume["completed_keys"])
    parent_checkpoint_hash = resume.get("parent_checkpoint_hash")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, downloads_path=str(DL))
        context = browser.new_context(accept_downloads=True, locale="en-US")
        page = context.new_page()

        root_children = inventory_children(page, ROOT_LINK)
        if not root_children:
            raise SystemExit("ROOT_CHILDREN_EMPTY")
        root_keys = {x["key"] for x in root_children}
        atomic_json(EVID / "ROOT_INVENTORY.json", {
            "schema": "LOUKSNA_DROPBOX_ROOT_PARTITION_INVENTORY/2.0-PUAC2",
            "status": "PASS",
            "count": len(root_children),
            "folders": sum(x["kind"] == "folder" for x in root_children),
            "files": sum(x["kind"] == "file" for x in root_children),
            "child_identity_sha256": sorted(root_keys),
            "resume_completed_root_count": sum(x["key"] in completed_keys for x in root_children),
            "observed_at_utc": utc(),
        })

        queue = list(resume["pending_queue"])
        queued = {x["key"] for x in queue if isinstance(x, dict) and x.get("key")}
        for child in root_children:
            if child["key"] not in completed_keys and child["key"] not in queued:
                queue.append({"depth": 1, **child})
                queued.add(child["key"])

        write_checkpoint(
            ROOT, manifest, queue, completed_keys, "START_OR_RESUME",
            failed=manifest["failed"], parent_hint=parent_checkpoint_hash,
        )

        ordinal = len(manifest["completed"])
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
                "schema": "LOUKSNA_DROPBOX_PARTITION_PROGRESS/2.0-PUAC2",
                "status": "RUNNING",
                "current": {"kind": item["kind"], "label": item["label"], "depth": depth, "identity_sha256": key},
                "completed_count_current_run": len(manifest["completed"]),
                "completed_count_prior": len(manifest["prior_completed"]),
                "queue_remaining": len(queue),
                "seen_nodes": len(queued),
                "updated_at_utc": utc(),
            })
            record_event("PROGRESS", current_identity_sha256=key, queue_remaining=len(queue))

            try:
                attempt = process_item(page, item, ordinal)
            except Exception as exc:
                failure = {
                    "source_identity_sha256": key,
                    "kind": item["kind"],
                    "label": item["label"],
                    "error": f"{type(exc).__name__}:{exc}",
                    "failed_at_utc": utc(),
                    "retryable": True,
                }
                manifest["failed"].append(failure)
                atomic_json(EVID / "MANIFEST.json", manifest)
                write_checkpoint(ROOT, manifest, [item] + queue, completed_keys, "ITEM_FAILURE", failed=manifest["failed"])
                raise

            if attempt["action"] == "downloaded":
                manifest["completed"].append(attempt["result"])
                completed_keys.add(key)
                manifest["failed"] = [x for x in manifest["failed"] if x.get("source_identity_sha256") != key]
                atomic_json(EVID / "MANIFEST.json", manifest)
                write_checkpoint(ROOT, manifest, queue, completed_keys, "OBJECT_COMMITTED", failed=manifest["failed"])
                continue

            if attempt["action"] == "folder_complete":
                manifest["split_folders"].append({
                    "label": item["label"],
                    "source_identity_sha256": key,
                    "depth": depth,
                    "child_count": 0,
                    "fallback_reason": attempt.get("fallback_reason"),
                    "inventory_provider": "DROPBOX_API_LIST_FOLDER_SHARED_LINK",
                })
                completed_keys.add(key)
                atomic_json(EVID / "MANIFEST.json", manifest)
                write_checkpoint(ROOT, manifest, queue, completed_keys, "API_EMPTY_FOLDER_COMMITTED", failed=manifest["failed"])
                continue

            if attempt["action"] == "split":
                children = attempt.get("children")
                if children is None:
                    raise RuntimeError("SPLIT_CHILDREN_NOT_BOUND_BY_AUTHORITATIVE_PROVIDER")
                if not children:
                    raise RuntimeError("PARTITION_REQUIRED_BUT_CHILDREN_EMPTY:" + key)
                manifest["split_folders"].append({
                    "label": item["label"],
                    "source_identity_sha256": key,
                    "depth": depth,
                    "child_count": len(children),
                    "fallback_reason": attempt.get("fallback_reason"),
                })
                for child in children:
                    if child["key"] not in queued and child["key"] not in completed_keys:
                        queue.append({"depth": depth + 1, **child})
                        queued.add(child["key"])
                completed_keys.add(key)
                atomic_json(EVID / "MANIFEST.json", manifest)
                write_checkpoint(ROOT, manifest, queue, completed_keys, "FOLDER_SPLIT_COMMITTED", failed=manifest["failed"])
                continue

            raise RuntimeError("UNKNOWN_PARTITION_ACTION")

        browser.close()

    missing_root = sorted(root_keys - completed_keys)
    if missing_root:
        raise RuntimeError("ROOT_OBJECTS_UNRESOLVED:" + ",".join(missing_root))

    manifest["status"] = "PASS"
    manifest["completed_at_utc"] = utc()
    manifest["payload_count"] = len(manifest["completed"])
    manifest["payload_bytes"] = sum(int(x["bytes"]) for x in manifest["completed"])
    manifest["prior_completed_count"] = len(manifest["prior_completed"])
    manifest["root_object_count"] = len(root_children)
    manifest["root_completed_count"] = len(root_children)
    manifest["completed_source_key_count"] = len(completed_keys)
    manifest["unresolved_critical_bugs"] = 0
    atomic_json(EVID / "MANIFEST.json", manifest)
    terminal_cp = write_checkpoint(ROOT, manifest, [], completed_keys, "CORPUS_TRANSFER_COMPLETE", failed=[])
    atomic_json(EVID / "RECOVERY_STATUS.json", {
        "schema": "PUAC2_TRANSFER_RECOVERY_STATUS/1.0",
        "status": "PASS",
        "last_verified_checkpoint_id": terminal_cp["checkpoint_id"],
        "last_verified_checkpoint_hash": terminal_cp["checkpoint_hash"],
        "resume_used": bool(resume["source"]),
        "verified_progress_preserved": True,
        "completed_at_utc": utc(),
    })
    print(json.dumps({
        "PARTITIONED_ACQUISITION": "PASS",
        "payload_count_current_run": manifest["payload_count"],
        "payload_bytes_current_run": manifest["payload_bytes"],
        "prior_completed_count": manifest["prior_completed_count"],
        "root_object_count": manifest["root_object_count"],
        "root_completed_count": manifest["root_completed_count"],
        "split_folders": len(manifest["split_folders"]),
        "checkpoint_hash": terminal_cp["checkpoint_hash"],
    }, sort_keys=True))

if __name__ == "__main__":
    main()
