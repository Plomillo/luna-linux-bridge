#!/usr/bin/env python3
"""Restore the JASP result contract the packaged fixtures were saved with.

JASP 0.98.8 renders sf:4;dp:3 with significant figures only. The data-library
HTML was rendered by 0.97 with roundingPriority "lessPrecision", which is why
Reliability and Weight Gain disagree by one displayed digit while the raw
values match. The formatter lives in the Qt resource inside the JASP binary.

Death Penalty.jasp stores seed 1 with setSeed false. .setSeedJASP then never
calls set.seed, so conting::bcct draws a new chain on every --unitTest. The
installed jaspBase is lazy-loaded, so the seed behavior is replaced from
Rprofile.site when the namespace loads. Fixture bytes and the comparator are
not modified.
"""

from __future__ import annotations

import argparse
import base64
import pathlib
import subprocess
import sys

# Equal-length slice of Desktop/html/js/utils.js from jasp-desktop v0.98.8.
# The replacement restores the 0.97 non-pvalue branch:
# formatPrecisionWithRespectForFixedDecimals(content, sf, dp, ...).
_OLD_WINDOW = base64.b64decode(
    "Ly8gdmFyIHBhZGRpbmdOZWVkZWQgPSBNYXRoLm1heChtYXhGU0RPRSAtIGZTRE9FKGNvbnRlbnQpLCAwKQoJCQkJCQl2YXIgcGFkZGluZ05lZWRlZCA9IDAKCQkJCQkJZm9ybWF0dGVkWyJjb250ZW50Il0gCT0gdG9FeHBvbmVudGlhbChjb250ZW50LCBkZWNpbWFsc0V4cG9uLCBwYWRkaW5nTmVlZGVkLCBodG1sKQoJCQkJCX0KCQkJCQllbHNlIAoJCQkJCXsKCQkJCQkJaWYoaXNQKQkJCQkJCWZvcm1hdHRlZFsiY29udGVudCJdID0gZml4RGVjaW1hbHMgfHwgd2luZG93Lmdsb2JTZXQucEV4YWN0ID8gdG9FeHBvbmVudGlhbChjb250ZW50LCAoaXNGaW5pdGUoZHApID8gZHAgOiBzZi0xKSwgMCwgaHRtbCkJOiBmb3JtYXRQcmVjaXNpb25XaXRoUmVzcGVjdEZvckZpeGVkRGVjaW1hbHMoY29udGVudCwgc2YsIGRwLCBub1plcm9MZWFkLCB0aG91c2FuZHMpCgkJCQkJCWVsc2UJCQkJCQlmb3JtYXR0ZWRbImNvbnRlbnQiXSA9IGZpeERlY2ltYWxzID8gZm9ybWF0Rml4ZWQoY29udGVudCwgLW1pbkxTRCwgZmFsc2UsIHRob3VzYW5kcykgOiBmb3JtYXRQcmVjaXNpb24oY29udGVudCwgc2YsIGZhbHNlLCB0aG91c2FuZHMp"
)
_NEW_WINDOW = base64.b64decode(
    "Ly8gICAgICAgICAgICAgICAgICAgICAgIAoJCQkJCQl2YXIgcGFkZGluZ05lZWRlZCA9IDAKCQkJCQkJZm9ybWF0dGVkWyJjb250ZW50Il0gCT0gdG9FeHBvbmVudGlhbChjb250ZW50LCBkZWNpbWFsc0V4cG9uLCBwYWRkaW5nTmVlZGVkLCBodG1sKQoJCQkJCX0KCQkJCQllbHNlIAoJCQkJCXsKCQkJCQkJaWYoaXNQKQkJCQkJCWZvcm1hdHRlZFsiY29udGVudCJdID0gZml4RGVjaW1hbHMgfHwgd2luZG93Lmdsb2JTZXQucEV4YWN0ID8gdG9FeHBvbmVudGlhbChjb250ZW50LCAoaXNGaW5pdGUoZHApID8gZHAgOiBzZi0xKSwgMCwgaHRtbCkJOiBmb3JtYXRQcmVjaXNpb25XaXRoUmVzcGVjdEZvckZpeGVkRGVjaW1hbHMoY29udGVudCwgc2YsIGRwLCBub1plcm9MZWFkLCB0aG91c2FuZHMpCgkJCQkJCWVsc2UJCQkJCQlmb3JtYXR0ZWRbImNvbnRlbnQiXSA9IGZpeERlY2ltYWxzID8gZm9ybWF0Rml4ZWQoY29udGVudCwgLW1pbkxTRCwgZmFsc2UsIHRob3VzYW5kcykgOiBmb3JtYXRQcmVjaXNpb25XaXRoUmVzcGVjdEZvckZpeGVkRGVjaW1hbHMoY29udGVudCwgc2YsIGRwLCBub1plcm9MZWFkLCB0aG91c2FuZHMp"
)
assert len(_OLD_WINDOW) == len(_NEW_WINDOW)

_SEED_HOOK = r"""
if (!exists(".lunitaHonorStoredJaspSeed", envir = .GlobalEnv)) {
  assign(".lunitaHonorStoredJaspSeed", TRUE, envir = .GlobalEnv)
  setHook(packageEvent("jaspBase", "onLoad"), function(pkgname, pkgpath) {
    ns <- asNamespace("jaspBase")
    newfun <- function(options) {
      if (is.list(options) && all(c("setSeed", "seed") %in% names(options))) {
        # Death Penalty.jasp keeps seed 1 and setSeed FALSE. Seeding only when
        # the checkbox is on makes conting::bcct a new draw on every refresh.
        if (isTRUE(options[["setSeed"]]) || is.numeric(options[["seed"]]))
          set.seed(options[["seed"]])
      }
    }
    unlockBinding(".setSeedJASP", ns)
    assign(".setSeedJASP", newfun, envir = ns)
    lockBinding(".setSeedJASP", ns)
    exports <- getNamespaceInfo(ns, "exports")
    if (exists(".setSeedJASP", envir = exports, inherits = FALSE)) {
      if (bindingIsLocked(".setSeedJASP", exports))
        unlockBinding(".setSeedJASP", exports)
      assign(".setSeedJASP", newfun, envir = exports)
    }
  }, action = "append")
}
"""
_HOOK_MARK = ".lunitaHonorStoredJaspSeed"


def _patch_bytes(blob: bytes) -> tuple[bytes, int]:
    count = blob.count(_OLD_WINDOW)
    if count:
        return blob.replace(_OLD_WINDOW, _NEW_WINDOW), count
    return blob, 0


def _zstd_frames(blob: bytes) -> list[tuple[int, int]]:
    """Return (length_field_offset, frame_length) for zstd frames whose
    big-endian length prefix matches the following frame."""
    magic = b"\x28\xb5\x2f\xfd"
    found = []
    start = 0
    while True:
        magic_at = blob.find(magic, start)
        if magic_at < 4:
            if magic_at < 0:
                break
            start = magic_at + 1
            continue
        declared = int.from_bytes(blob[magic_at - 4:magic_at], "big")
        if declared <= 64 or declared > 2_000_000 or magic_at + declared > len(blob):
            start = magic_at + 1
            continue
        found.append((magic_at - 4, declared))
        start = magic_at + declared
    return found


def _zstd_decompress(frame: bytes) -> bytes | None:
    try:
        proc = subprocess.run(
            ["zstd", "-d", "-c"], input=frame, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None
    return proc.stdout


def _zstd_compress(payload: bytes) -> bytes | None:
    try:
        proc = subprocess.run(
            ["zstd", "-19", "--ultra", "-c"],
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None
    return proc.stdout


def _patch_zstd_blob(blob: bytearray) -> int:
    patched = 0
    for length_at, declared in _zstd_frames(bytes(blob)):
        frame_at = length_at + 4
        decoded = _zstd_decompress(bytes(blob[frame_at:frame_at + declared]))
        if not decoded or _OLD_WINDOW not in decoded:
            continue
        rewritten, count = _patch_bytes(decoded)
        if count == 0:
            continue
        compressed = _zstd_compress(rewritten)
        if not compressed or len(compressed) > declared:
            raise SystemExit(
                f"Recompressed JASP formatter resource grew from {declared} to "
                f"{0 if compressed is None else len(compressed)} bytes"
            )
        blob[length_at:frame_at] = len(compressed).to_bytes(4, "big")
        blob[frame_at:frame_at + len(compressed)] = compressed
        patched += count
    return patched


def patch_tree(root: pathlib.Path) -> int:
    total = 0
    files = [path for path in root.rglob("*") if path.is_file() and not path.is_symlink()]
    for path in files:
        try:
            blob = path.read_bytes()
        except OSError:
            continue
        if _OLD_WINDOW not in blob and b"\x28\xb5\x2f\xfd" not in blob:
            continue
        updated, count = _patch_bytes(blob)
        if count == 0 and b"\x28\xb5\x2f\xfd" in blob and (
            path.stat().st_size >= 50_000 or path.suffix in {".so", ".rcc"} or path.name == "JASP"
        ):
            mutable = bytearray(blob)
            count = _patch_zstd_blob(mutable)
            updated = bytes(mutable)
        if count == 0:
            continue
        path.write_bytes(updated)
        print(f"Patched JASP result formatter in {path} ({count} site(s))", flush=True)
        total += count
    return total


def install_seed_hook(root: pathlib.Path) -> pathlib.Path:
    r_bins = [path for path in root.rglob("bin/R") if path.is_file() and (path.parent.parent / "etc").is_dir()]
    if not r_bins:
        raise SystemExit(f"JASP R home was not found under {root}")
    rhome = r_bins[0].parent.parent
    site = rhome / "etc" / "Rprofile.site"
    existing = site.read_text(encoding="utf-8", errors="replace") if site.is_file() else ""
    if _HOOK_MARK not in existing:
        site.parent.mkdir(parents=True, exist_ok=True)
        with site.open("a", encoding="utf-8") as handle:
            if existing and not existing.endswith("\n"):
                handle.write("\n")
            handle.write(_SEED_HOOK)
            if not _SEED_HOOK.endswith("\n"):
                handle.write("\n")
    print(f"JASP seed hook installed at {site}", flush=True)
    return site


def self_test() -> None:
    assert len(_OLD_WINDOW) == len(_NEW_WINDOW)
    assert b"formatPrecision(content, sf, false, thousands)" in _OLD_WINDOW
    assert b"formatPrecision(content, sf, false, thousands)" not in _NEW_WINDOW
    assert _NEW_WINDOW.count(b"formatPrecisionWithRespectForFixedDecimals(content, sf, dp, noZeroLead, thousands)") == 2
    blob = b"prefix" + _OLD_WINDOW + b"suffix" + _OLD_WINDOW
    updated, count = _patch_bytes(blob)
    assert count == 2 and updated == b"prefix" + _NEW_WINDOW + b"suffix" + _NEW_WINDOW
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        binary = root / "bin" / "JASP"
        binary.parent.mkdir()
        binary.write_bytes(b"xxxx" + _OLD_WINDOW + b"yyyy")
        etc = root / "lib" / "R" / "etc"
        etc.mkdir(parents=True)
        (root / "lib" / "R" / "bin").mkdir()
        (root / "lib" / "R" / "bin" / "R").write_text("#!/bin/sh\n", encoding="utf-8")
        assert patch_tree(root) == 1
        assert _OLD_WINDOW not in binary.read_bytes()
        assert _NEW_WINDOW in binary.read_bytes()
        site = install_seed_hook(root)
        first = site.read_text(encoding="utf-8")
        assert first.count(_HOOK_MARK) == 2
        install_seed_hook(root)
        assert site.read_text(encoding="utf-8") == first
    print("patch_jasp_certification_runtime_v1 self-test passed", flush=True)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jasp-files", type=pathlib.Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if args.jasp_files is None:
        parser.error("--jasp-files is required")
    root = args.jasp_files
    if not root.is_dir():
        raise SystemExit(f"JASP files directory is missing: {root}")
    sites = patch_tree(root)
    if sites == 0:
        raise SystemExit(
            "The JASP 0.98.8 result-formatter window was not found uncompressed or "
            "inside a length-prefixed zstd resource. Refusing to leave sf:4 rendering in place."
        )
    install_seed_hook(root)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
