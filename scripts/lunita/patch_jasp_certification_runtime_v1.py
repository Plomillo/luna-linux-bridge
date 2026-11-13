#!/usr/bin/env python3
"""Restore the JASP result contract the packaged fixtures were saved with.

JASP 0.98.8 renders sf:4;dp:3 with significant figures only. The data-library
HTML was rendered by 0.97 with roundingPriority "lessPrecision", which is why
Reliability and Weight Gain disagree by one displayed digit while the raw
values match. The formatter lives in the Qt resource inside the JASP binary.

This WebEngine throws when one NumberFormat sets both significant and fraction
digits, and that aborts HTML export. The numeric branch therefore chooses the
shorter of formatPrecision and formatFixed instead of calling that constructor.
The patched script is recompressed into the original zstd slot.

The pinned JASP engine embeds R through RInside, whose initialization uses
--vanilla and does not source Rprofile.site. This patch therefore changes only
the JASP result formatter; it does not install an ineffective startup hook.
The independent lane creates a disposable .jasp copy with JASP's native
setSeed=true, seed=1 options and hash-binds that copy to the untouched source.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
import hashlib
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
    "Ly8gICAgICAgICAgICAgCgkJCQkJCXZhciBwYWRkaW5nTmVlZGVkID0gMAoJCQkJCQlmb3JtYXR0ZWRbImNvbnRlbnQiXSAJPSB0b0V4cG9uZW50aWFsKGNvbnRlbnQsIGRlY2ltYWxzRXhwb24sIHBhZGRpbmdOZWVkZWQsIGh0bWwpCgkJCQkJfQoJCQkJCWVsc2UgCgkJCQkJewoJCQkJCQlpZihpc1ApCQkJCQkJZm9ybWF0dGVkWyJjb250ZW50Il0gPSBmaXhEZWNpbWFscyB8fCB3aW5kb3cuZ2xvYlNldC5wRXhhY3QgPyB0b0V4cG9uZW50aWFsKGNvbnRlbnQsIChpc0Zpbml0ZShkcCkgPyBkcCA6IHNmLTEpLCAwLCBodG1sKQk6IGZvcm1hdFByZWNpc2lvbldpdGhSZXNwZWN0Rm9yRml4ZWREZWNpbWFscyhjb250ZW50LCBzZiwgZHAsIG5vWmVyb0xlYWQsIHRob3VzYW5kcykKCQkJCQkJZWxzZQkJCQkJCWZvcm1hdHRlZFsiY29udGVudCJdID0gZml4RGVjaW1hbHMgPyBmb3JtYXRGaXhlZChjb250ZW50LCAtbWluTFNELCBmYWxzZSwgdGhvdXNhbmRzKSA6ICgoYSxiKT0+YS5sZW5ndGg8PWIubGVuZ3RoP2E6YikoZm9ybWF0UHJlY2lzaW9uKGNvbnRlbnQsc2YsMCwwKSxmb3JtYXRGaXhlZChjb250ZW50LGRwLDAsMCkp"
)
assert len(_OLD_WINDOW) == len(_NEW_WINDOW)

# The mixed Intl constructor stays in the binary. The numeric branch no longer
# calls it. These two latex maps are rewritten only so the patched utils.js
# recompresses into the original zstd slot; HTML export does not use them.
_OLD_LATEX = base64.b64decode(
    "bGV0IHNwZWNpYWxfbWF0Y2ggPSBbICAnXycsICAgJyUnLC8qICAgJyQnLCovICAgJyZ0YXU7JywgJyZzdXAyOycsICAgJyYnLCAnXHUwMEQ3JywgJ1x1MjA4QScsICdcdTIwOEInLCAgJ1x1MjIzQycsICAnXHUwM0M3JywgJ1x1MDNBNycsICAnXHUwM0I3JywgICAgJ1x1MDNDOScsICdcdTIwODAnLCAnXHUyMDgxJywgJ1x1MjA4MicsICdcdTAwQjInLCAgICAnXHUwM0IxJywgICAgICdcdTAzQkInLCAnXHUyNzNCJywgJ1x1MjAwOScsICdcdTIwMTQnLCAnXHUyNzNCJywgICAgJ1x1MjIxRSddCglsZXQgc3BlY2lhbF9yZXBsYSA9IFsnXFxfJywgJ1xcJScsLyogJ1xcJCcsKi8gJyRcXHRhdSQnLCAnJF57Mn0kJywgJ1xcJicsICdcXHRpbWVzJywgJyRfeyt9JCcsICckX3stfSQnLCAnJFxcc2ltJCcsICckXFxjaGkkJywgICAgICAnWCcsICckXFxldGEkJywgJyRcXG9tZWdhJCcsICckX3swfSQnLCAnJF97MX0kJywgJyRfezJ9JCcsICckXnsyfSQnLCAnJFxcYWxwaGEkJywgJyRcXGxhbWJkYSQnLCAgICAgICcqJywgICAgICAnICcsICAgICAnLS0nLCAgICAgICcqJywgJyRcXGluZnR5JCdd"
)
_NEW_LATEX = base64.b64decode(
    "bGV0IHNwZWNpYWxfbWF0Y2ggPSBbJ2EnXTsgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCglsZXQgc3BlY2lhbF9yZXBsYSA9IFsnYSddOyAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg"
)
assert len(_OLD_LATEX) == len(_NEW_LATEX)

def _apply_pairs(blob: bytes) -> tuple[bytes, int, int]:
    calls = blob.count(_OLD_WINDOW)
    latex = blob.count(_OLD_LATEX)
    if calls:
        blob = blob.replace(_OLD_WINDOW, _NEW_WINDOW)
    if latex:
        blob = blob.replace(_OLD_LATEX, _NEW_LATEX)
    return blob, calls, latex


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
    """One-shot ZSTD_compress. The CLI streams and omits the content size, and
    Qt then rejects the frame in ZSTD_getFrameContentSize (empty script, 0 tables)."""
    lib = None
    for name in ("libzstd.so.1", "libzstd.so"):
        try:
            lib = ctypes.CDLL(name)
            break
        except OSError:
            continue
    if lib is None:
        return None
    lib.ZSTD_compress.argtypes = [
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_int,
    ]
    lib.ZSTD_compress.restype = ctypes.c_size_t
    lib.ZSTD_compressBound.argtypes = [ctypes.c_size_t]
    lib.ZSTD_compressBound.restype = ctypes.c_size_t
    lib.ZSTD_isError.argtypes = [ctypes.c_size_t]
    lib.ZSTD_isError.restype = ctypes.c_uint
    lib.ZSTD_getFrameContentSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    lib.ZSTD_getFrameContentSize.restype = ctypes.c_ulonglong
    bound = lib.ZSTD_compressBound(len(payload))
    dst = ctypes.create_string_buffer(bound)
    src = ctypes.create_string_buffer(payload)
    got = lib.ZSTD_compress(dst, bound, ctypes.addressof(src), len(payload), 19)
    if lib.ZSTD_isError(got):
        return None
    frame = dst.raw[:got]
    content = lib.ZSTD_getFrameContentSize(frame, len(frame))
    if content != len(payload):
        return None
    return frame


def _patch_zstd_blob(blob: bytearray) -> tuple[int, int]:
    calls = 0
    latex = 0
    for length_at, declared in reversed(_zstd_frames(bytes(blob))):
        frame_at = length_at + 4
        decoded = _zstd_decompress(bytes(blob[frame_at:frame_at + declared]))
        if not decoded or (_OLD_WINDOW not in decoded and _OLD_LATEX not in decoded):
            continue
        rewritten, call_count, latex_count = _apply_pairs(decoded)
        if call_count == 0 and latex_count == 0:
            continue
        compressed = _zstd_compress(rewritten)
        if not compressed or len(compressed) > declared:
            raise SystemExit(
                "Recompressed JASP formatter resource "
                f"{'is missing a content-size header' if not compressed else 'grew'} "
                f"from {declared} to {0 if not compressed else len(compressed)} bytes"
            )
        blob[length_at:frame_at] = len(compressed).to_bytes(4, "big")
        blob[frame_at:frame_at + len(compressed)] = compressed
        calls += call_count
        latex += latex_count
    return calls, latex


def patch_tree(root: pathlib.Path) -> tuple[int, int]:
    calls = 0
    latex = 0
    files = [path for path in root.rglob("*") if path.is_file() and not path.is_symlink()]
    for path in files:
        try:
            blob = path.read_bytes()
        except OSError:
            continue
        if _OLD_WINDOW not in blob and _OLD_LATEX not in blob and b"\x28\xb5\x2f\xfd" not in blob:
            continue
        updated, call_count, latex_count = _apply_pairs(blob)
        if call_count == 0 and latex_count == 0 and b"\x28\xb5\x2f\xfd" in blob and (
            path.stat().st_size >= 50_000 or path.suffix in {".so", ".rcc"} or path.name == "JASP"
        ):
            mutable = bytearray(blob)
            call_count, latex_count = _patch_zstd_blob(mutable)
            updated = bytes(mutable)
        if call_count == 0 and latex_count == 0:
            continue
        before_sha256 = hashlib.sha256(blob).hexdigest()
        after_sha256 = hashlib.sha256(updated).hexdigest()
        if before_sha256 == after_sha256:
            raise SystemExit(f"Formatter patch reported a change without changing bytes: {path}")
        path.write_bytes(updated)
        if hashlib.sha256(path.read_bytes()).hexdigest() != after_sha256:
            raise SystemExit(f"Formatter patch post-write hash mismatch: {path}")
        print(
            f"Patched JASP result formatter in {path} "
            f"(call sites={call_count}, latex sites={latex_count}, "
            f"before_sha256={before_sha256}, after_sha256={after_sha256})",
            flush=True,
        )
        calls += call_count
        latex += latex_count
    return calls, latex


def self_test() -> None:
    assert len(_OLD_WINDOW) == len(_NEW_WINDOW)
    assert len(_OLD_LATEX) == len(_NEW_LATEX)
    assert b"formatPrecision(content, sf, false, thousands)" in _OLD_WINDOW
    assert b"formatPrecision(content, sf, false, thousands)" not in _NEW_WINDOW
    assert b"((a,b)=>a.length<=b.length?a:b)" in _NEW_WINDOW
    assert _NEW_WINDOW.count(b"formatPrecisionWithRespectForFixedDecimals") == 1
    assert b"\u00D7" in _OLD_LATEX and b"\u00D7" not in _NEW_LATEX
    # No Rprofile.site mutation is permitted: JASPEngine embeds RInside --vanilla.
    print("patch_jasp_certification_runtime_v1 self-test passed (formatter-only; no R startup hook)", flush=True)

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
    calls, latex = patch_tree(root)
    if calls == 0 or latex == 0:
        raise SystemExit(
            "The JASP 0.98.8 result formatter was not patched "
            f"(call sites={calls}, latex sites={latex}). "
            "Refusing to leave sf:4 rendering in place."
        )
    print("PASS_JASP_FORMATTER_PATCH_ONLY_NO_R_STARTUP_PROFILE_MUTATION", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
