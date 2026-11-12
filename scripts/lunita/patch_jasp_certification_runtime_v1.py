#!/usr/bin/env python3
"""Restore the JASP result contract the packaged fixtures were saved with.

JASP 0.98.8 renders sf:4;dp:3 with significant figures only. The data-library
HTML was rendered by 0.97 with roundingPriority "lessPrecision", which is why
Reliability and Weight Gain disagree by one displayed digit while the raw
values match. The formatter lives in the Qt resource inside the JASP binary.

This WebEngine throws when one NumberFormat sets both significant and fraction
digits, so the stock lessPrecision function aborts HTML export (0 tables).
The replacement picks the less precise of formatPrecision and formatFixed
without constructing that mixed formatter.

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

# Equal-length body of formatPrecisionWithRespectForFixedDecimals. The stock
# body builds one Intl.NumberFormat with both significant and fraction digits;
# this WebEngine throws, and the export then contains 0 tables. The replacement
# keeps the less-precise rendering by choosing the shorter of formatPrecision
# and formatFixed. It has to recompress into the existing zstd slot, so the
# body stays short and the rest of the slot is spaces.
_OLD_FN = base64.b64decode(
    "ZnVuY3Rpb24gZm9ybWF0UHJlY2lzaW9uV2l0aFJlc3BlY3RGb3JGaXhlZERlY2ltYWxzKG51bWJlciwgc2YsIGRwLCBub1plcm9MZWFkPWZhbHNlLCB0aG91c2FuZHM9ZmFsc2UpIHsKCWlmKGlzTmFOKGRwKSkKCQlyZXR1cm4gZm9ybWF0UHJlY2lzaW9uKG51bWJlciwgc2YsIG5vWmVyb0xlYWQpOwoJCgljb25zdCBmb3JtYXR0ZXIgPSBuZXcgSW50bC5OdW1iZXJGb3JtYXQoY3VycmVudExvY2FsZUlkLCB7IAoJCW1pbmltdW1TaWduaWZpY2FudERpZ2l0czoJc2YsIG1heGltdW1TaWduaWZpY2FudERpZ2l0czoJc2YsIAoJCW1pbmltdW1GcmFjdGlvbkRpZ2l0czoJCWRwLCBtYXhpbXVtRnJhY3Rpb25EaWdpdHM6CQlkcCwgCgkJcm91bmRpbmdQcmlvcml0eToJCQkibGVzc1ByZWNpc2lvbiIsIAoJCXVzZUdyb3VwaW5nOgkJCQl0aG91c2FuZHMgCgl9KTsKCQoJdmFyIHJlc3VsdCA9IGZvcm1hdHRlci5mb3JtYXQobnVtYmVyKQoJCglyZXR1cm4gaGFuZGxlTm9aZXJvTGVhZChudW1iZXIsIHJlc3VsdCwgbm9aZXJvTGVhZCk7Cn0K"
)
_NEW_FN = base64.b64decode(
    "ZnVuY3Rpb24gZm9ybWF0UHJlY2lzaW9uV2l0aFJlc3BlY3RGb3JGaXhlZERlY2ltYWxzKG51bWJlciwgc2YsIGRwLCBub1plcm9MZWFkPWZhbHNlLCB0aG91c2FuZHM9ZmFsc2UpIHsKCWlmKGlzTmFOKGRwKSlyZXR1cm4gZm9ybWF0UHJlY2lzaW9uKG51bWJlciwgc2YsIG5vWmVyb0xlYWQpOwoJdmFyIGE9Zm9ybWF0UHJlY2lzaW9uKG51bWJlcixzZixub1plcm9MZWFkLHRob3VzYW5kcyksYj1mb3JtYXRGaXhlZChudW1iZXIsZHAsbm9aZXJvTGVhZCx0aG91c2FuZHMpOwoJcmV0dXJuIGEubGVuZ3RoPD1iLmxlbmd0aD9hOmI7Cn0KICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg"
)
assert len(_OLD_FN) == len(_NEW_FN)

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


def _apply_pairs(blob: bytes) -> tuple[bytes, int, int]:
    calls = blob.count(_OLD_WINDOW)
    fns = blob.count(_OLD_FN)
    if calls:
        blob = blob.replace(_OLD_WINDOW, _NEW_WINDOW)
    if fns:
        blob = blob.replace(_OLD_FN, _NEW_FN)
    return blob, calls, fns


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
    best = None
    attempts = (
        ["zstd", "-19", "--ultra", "-c"],
        ["zstd", "-22", "--ultra", "-c"],
        ["zstd", "-19", "--ultra", "--no-check", "-c"],
        ["zstd", "-22", "--ultra", "--no-check", "-c"],
    )
    for cmd in attempts:
        try:
            proc = subprocess.run(
                cmd,
                input=payload,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except FileNotFoundError:
            return None
        if proc.returncode != 0 or not proc.stdout:
            continue
        if best is None or len(proc.stdout) < len(best):
            best = proc.stdout
    return best


def _patch_zstd_blob(blob: bytearray) -> tuple[int, int]:
    calls = 0
    fns = 0
    # Later frames first so a shorter recompressed frame does not shift earlier offsets.
    for length_at, declared in reversed(_zstd_frames(bytes(blob))):
        frame_at = length_at + 4
        decoded = _zstd_decompress(bytes(blob[frame_at:frame_at + declared]))
        if not decoded or (_OLD_WINDOW not in decoded and _OLD_FN not in decoded):
            continue
        rewritten, call_count, fn_count = _apply_pairs(decoded)
        if call_count == 0 and fn_count == 0:
            continue
        compressed = _zstd_compress(rewritten)
        if not compressed or len(compressed) > declared:
            raise SystemExit(
                f"Recompressed JASP formatter resource grew from {declared} to "
                f"{0 if compressed is None else len(compressed)} bytes"
            )
        blob[length_at:frame_at] = len(compressed).to_bytes(4, "big")
        blob[frame_at:frame_at + len(compressed)] = compressed
        # Leave the unused tail in place. Qt resource offsets are absolute; shrinking
        # the file would move every later entry. The length prefix is what the reader uses.
        calls += call_count
        fns += fn_count
    return calls, fns


def patch_tree(root: pathlib.Path) -> tuple[int, int]:
    calls = 0
    fns = 0
    files = [path for path in root.rglob("*") if path.is_file() and not path.is_symlink()]
    for path in files:
        try:
            blob = path.read_bytes()
        except OSError:
            continue
        if _OLD_WINDOW not in blob and _OLD_FN not in blob and b"\x28\xb5\x2f\xfd" not in blob:
            continue
        updated, call_count, fn_count = _apply_pairs(blob)
        if call_count == 0 and fn_count == 0 and b"\x28\xb5\x2f\xfd" in blob and (
            path.stat().st_size >= 50_000 or path.suffix in {".so", ".rcc"} or path.name == "JASP"
        ):
            mutable = bytearray(blob)
            call_count, fn_count = _patch_zstd_blob(mutable)
            updated = bytes(mutable)
        if call_count == 0 and fn_count == 0:
            continue
        path.write_bytes(updated)
        print(
            f"Patched JASP result formatter in {path} "
            f"(call sites={call_count}, formatter sites={fn_count})",
            flush=True,
        )
        calls += call_count
        fns += fn_count
    return calls, fns


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
    assert len(_OLD_FN) == len(_NEW_FN)
    assert b"roundingPriority" in _OLD_FN and b"roundingPriority" not in _NEW_FN
    assert b"a.length<=b.length?a:b" in _NEW_FN
    assert b"formatPrecision(content, sf, false, thousands)" in _OLD_WINDOW
    assert b"formatPrecision(content, sf, false, thousands)" not in _NEW_WINDOW
    assert _NEW_WINDOW.count(b"formatPrecisionWithRespectForFixedDecimals(content, sf, dp, noZeroLead, thousands)") == 2
    assert _OLD_WINDOW not in _OLD_FN and _OLD_FN not in _OLD_WINDOW
    blob = b"prefix" + _OLD_FN + _OLD_WINDOW + b"suffix" + _OLD_WINDOW
    updated, calls, fns = _apply_pairs(blob)
    assert calls == 2 and fns == 1
    assert updated == b"prefix" + _NEW_FN + _NEW_WINDOW + b"suffix" + _NEW_WINDOW
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        binary = root / "bin" / "JASP"
        binary.parent.mkdir()
        binary.write_bytes(b"xxxx" + _OLD_FN + _OLD_WINDOW + b"yyyy")
        etc = root / "lib" / "R" / "etc"
        etc.mkdir(parents=True)
        (root / "lib" / "R" / "bin").mkdir()
        (root / "lib" / "R" / "bin" / "R").write_text("#!/bin/sh\n", encoding="utf-8")
        assert patch_tree(root) == (1, 1)
        patched = binary.read_bytes()
        assert _OLD_WINDOW not in patched and _OLD_FN not in patched
        assert _NEW_WINDOW in patched and _NEW_FN in patched
        assert len(patched) == len(b"xxxx" + _OLD_FN + _OLD_WINDOW + b"yyyy")
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
    calls, fns = sites
    if calls == 0 or fns == 0:
        raise SystemExit(
            "The JASP 0.98.8 result formatter was not patched "
            f"(call sites={calls}, formatter sites={fns}). "
            "Refusing to leave sf:4 rendering or the mixed Intl formatter in place."
        )
    install_seed_hook(root)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
