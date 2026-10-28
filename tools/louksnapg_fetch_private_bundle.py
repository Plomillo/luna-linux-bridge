#!/usr/bin/env python3
"""Fetch an authenticated private candidate bundle without forwarding credentials cross-origin."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MAX_BYTES = 2_000_000_000


def origin(url: str) -> tuple[str, str, int | None]:
    parsed = urllib.parse.urlparse(url)
    port = parsed.port
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), port


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlparse(newurl).scheme.lower() != "https":
            raise urllib.error.HTTPError(newurl, code, "HTTPS_REDIRECT_REQUIRED", headers, fp)
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None and origin(req.full_url) != origin(newurl):
            for collection in (new_req.headers, new_req.unredirected_hdrs):
                for name in list(collection):
                    if name.lower() == "authorization":
                        del collection[name]
        return new_req


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    url = os.environ.get("LOUKSNAPG_PRIVATE_BUNDLE_URL", "")
    token = os.environ.get("LOUKSNAPG_PRIVATE_BUNDLE_TOKEN", "")
    if not url or not token:
        raise SystemExit("PRIVATE_BUNDLE_URL_OR_TOKEN_MISSING")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise SystemExit("PRIVATE_BUNDLE_URL_MUST_BE_HTTPS_WITHOUT_EMBEDDED_CREDENTIALS")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    descriptor = manifest.get("private_bundle", {})
    expected_size = descriptor.get("bytes")
    expected_sha = descriptor.get("sha256")
    if not isinstance(expected_size, int) or not 0 < expected_size <= MAX_BYTES:
        raise SystemExit("PRIVATE_BUNDLE_SIZE_OUT_OF_BOUNDS")
    if not isinstance(expected_sha, str) or len(expected_sha) != 64 or any(c not in "0123456789abcdef" for c in expected_sha):
        raise SystemExit("PRIVATE_BUNDLE_SHA256_INVALID")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("PRIVATE_BUNDLE_OUTPUT_ALREADY_EXISTS")

    request = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/octet-stream",
            "User-Agent": "LOUKSNAPG-private-candidate-fetch/1.0",
        },
        method="GET",
    )
    opener = urllib.request.build_opener(SafeRedirectHandler())
    written = 0
    digest = hashlib.sha256()
    try:
        with opener.open(request, timeout=45) as response, args.out.open("xb") as output:
            status = getattr(response, "status", 200)
            if status != 200:
                raise SystemExit("PRIVATE_BUNDLE_HTTP_STATUS_INVALID:" + str(status))
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    if int(content_length) != expected_size:
                        raise SystemExit("PRIVATE_BUNDLE_CONTENT_LENGTH_MISMATCH")
                except ValueError:
                    raise SystemExit("PRIVATE_BUNDLE_CONTENT_LENGTH_INVALID")
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                written += len(block)
                if written > expected_size or written > MAX_BYTES:
                    raise SystemExit("PRIVATE_BUNDLE_DOWNLOAD_SIZE_LIMIT_EXCEEDED")
                digest.update(block)
                output.write(block)
        actual_sha = digest.hexdigest()
        if written != expected_size or actual_sha != expected_sha:
            raise SystemExit("PRIVATE_BUNDLE_DOWNLOADED_IDENTITY_MISMATCH")
        print(json.dumps({
            "schema": "LOUKSNAPG_PRIVATE_BUNDLE_DOWNLOAD/1.0",
            "status": "PASS_PRIVATE_BUNDLE_IDENTITY",
            "bytes": written,
            "sha256": actual_sha,
            "authorization_forwarded_cross_origin": False,
            "secret_values_logged": False,
        }, sort_keys=True))
    except BaseException:
        try:
            args.out.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
