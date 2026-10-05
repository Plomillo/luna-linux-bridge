#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, re, time, hashlib
from datetime import datetime, timezone

SHARED_LINK = "https://www.dropbox.com/scl/fo/0dhs5jhwksqtmwl26vusi/AIIzeblluaJfhuXh9EnP-10?rlkey=p712fwlkbwn9g0dtybu2sf159&st=3igdng0g&dl=0"

ROOT = pathlib.Path(os.environ["STATE_ROOT"])
EVID = ROOT / "evidence"
DL = ROOT / "browser-downloads"
PAYLOAD = ROOT / "payload"
for p in (EVID, DL, PAYLOAD):
    p.mkdir(parents=True, exist_ok=True)

def utc():
    return datetime.now(timezone.utc).isoformat()

def atomic(path: pathlib.Path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def sanitize_url(url: str):
    try:
        from urllib.parse import urlsplit, parse_qsl
        u=urlsplit(url)
        return {
            "scheme":u.scheme,
            "host":u.hostname,
            "path":u.path,
            "query_keys":sorted({k for k,_ in parse_qsl(u.query,keep_blank_values=True)}),
        }
    except Exception:
        return {"sha256":hashlib.sha256(url.encode()).hexdigest()}

def main():
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    network=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True, downloads_path=str(DL))
        context=browser.new_context(accept_downloads=True, locale="en-US")
        page=context.new_page()

        def on_response(resp):
            try:
                h=resp.headers
                rec={
                    "utc":utc(),
                    "status":resp.status,
                    "url":sanitize_url(resp.url),
                    "content_type":h.get("content-type",""),
                    "content_disposition":h.get("content-disposition",""),
                    "content_length":h.get("content-length",""),
                    "x_dropbox_request_id":h.get("x-dropbox-request-id",""),
                }
                if (
                    "download" in resp.url.lower()
                    or "dropboxusercontent" in resp.url.lower()
                    or "zip" in rec["content_type"].lower()
                    or "attachment" in rec["content_disposition"].lower()
                ):
                    network.append(rec)
                    atomic(EVID/"NETWORK_CANDIDATES.json",{"schema":"LOUKSNA_DROPBOX_BROWSER_NETWORK/1.0","responses":network[-200:]})
            except Exception:
                pass
        page.on("response", on_response)

        page.goto(SHARED_LINK, wait_until="domcontentloaded", timeout=120000)
        atomic(EVID/"PAGE_LOADED.json",{
            "schema":"LOUKSNA_DROPBOX_CLOUD_BROWSER_PAGE/1.0",
            "status":"PASS","title":page.title(),"url":sanitize_url(page.url),
            "execution_plane":"GITHUB_HOSTED_UBUNTU_24_04","utc":utc()
        })

        for txt in ("Accept","Accept all","Reject all","Aceptar","Aceptar todas","Rechazar todas"):
            try:
                loc=page.get_by_text(txt, exact=True)
                if loc.count() and loc.first.is_visible():
                    loc.first.click(timeout=2000)
                    break
            except Exception:
                pass

        for pat in (re.compile("close",re.I),re.compile("not now",re.I),re.compile("cerrar",re.I),re.compile("ahora no",re.I)):
            try:
                loc=page.get_by_role("button", name=pat)
                if loc.count() and loc.first.is_visible():
                    loc.first.click(timeout=1500)
            except Exception:
                pass

        primary=page.locator('button[data-testid="action-bar-download-button"]')
        if not primary.count():
            (EVID/"PAGE_NO_DOWNLOAD_BUTTON.html").write_text(page.content(),encoding="utf-8")
            page.screenshot(path=str(EVID/"PAGE_NO_DOWNLOAD_BUTTON.png"),full_page=True)
            raise SystemExit("DROPBOX_DOWNLOAD_BUTTON_NOT_FOUND")
        primary.first.click(timeout=10000)
        atomic(EVID/"PRIMARY_CLICK.json",{
            "schema":"LOUKSNA_DROPBOX_BROWSER_CLICK/1.0","status":"PASS",
            "selector":'button[data-testid="action-bar-download-button"]',"utc":utc()
        })

        continuation=None
        selectors=[
            'button:has-text("Or continue with download only")',
            'button:has-text("Continue with download only")',
            'button:has-text("continuar solo con la descarga")',
        ]
        deadline=time.time()+45
        while time.time()<deadline and continuation is None:
            for selector in selectors:
                loc=page.locator(selector)
                try:
                    if loc.count() and loc.first.is_visible():
                        continuation=loc.first
                        break
                except Exception:
                    pass
            if continuation is None:
                time.sleep(0.25)

        if continuation is None:
            (EVID/"PAGE_AFTER_PRIMARY.html").write_text(page.content(),encoding="utf-8")
            page.screenshot(path=str(EVID/"PAGE_AFTER_PRIMARY.png"),full_page=True)
            raise SystemExit("DROPBOX_DOWNLOAD_CONTINUATION_NOT_FOUND")

        atomic(EVID/"CONTINUATION_VISIBLE.json",{
            "schema":"LOUKSNA_DROPBOX_BROWSER_CONTINUATION/1.0","status":"PASS",
            "text":"Or continue with download only","utc":utc()
        })

        try:
            with page.expect_download(timeout=180000) as info:
                continuation.click(timeout=10000)
            download=info.value
        except PlaywrightTimeoutError:
            (EVID/"PAGE_AFTER_CONTINUATION_TIMEOUT.html").write_text(page.content(),encoding="utf-8")
            page.screenshot(path=str(EVID/"PAGE_AFTER_CONTINUATION_TIMEOUT.png"),full_page=True)
            raise SystemExit("DROPBOX_BROWSER_DOWNLOAD_EVENT_TIMEOUT")

        atomic(EVID/"DOWNLOAD_EVENT.json",{
            "schema":"LOUKSNA_DROPBOX_BROWSER_DOWNLOAD_EVENT/1.0",
            "status":"PASS",
            "suggested_filename":download.suggested_filename,
            "execution_plane":"GITHUB_HOSTED_UBUNTU_24_04",
            "utc":utc()
        })

        final=PAYLOAD/(download.suggested_filename or "1. PROYECTOS PRIORITARIOS.zip")
        download.save_as(str(final))
        failure=download.failure()
        if failure:
            raise SystemExit("DROPBOX_BROWSER_DOWNLOAD_FAILURE:"+failure)

        atomic(EVID/"BROWSER_DOWNLOAD_COMPLETE.json",{
            "schema":"LOUKSNA_DROPBOX_BROWSER_DOWNLOAD_COMPLETE/1.0",
            "status":"PASS",
            "path":final.name,
            "bytes":final.stat().st_size,
            "sha256":hashlib.sha256(final.read_bytes()).hexdigest() if final.stat().st_size <= 64*1024*1024 else None,
            "execution_plane":"GITHUB_HOSTED_UBUNTU_24_04",
            "utc":utc()
        })
        browser.close()

if __name__=="__main__":
    main()
