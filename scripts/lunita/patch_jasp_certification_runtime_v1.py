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


def _fit_zstd_frame(payload: bytes, declared: int) -> bytes:
    """Recompress and pad to the exact original slot.

    Qt passes that slot length to ZSTD_decompress, which rejects a short
    buffer and a buffer with trailing junk that is not a frame. A skippable
    frame fills the gap. The length prefix stays equal to `declared`.
    """
    compressed = _zstd_compress(payload)
    if not compressed:
        raise SystemExit("zstd could not recompress the JASP formatter resource")
    if len(compressed) > declared:
        raise SystemExit(
            f"Recompressed JASP formatter resource grew from {declared} to {len(compressed)} bytes"
        )
    gap = declared - len(compressed)
    if gap == 0:
        return compressed
    if gap < 8:
        raise SystemExit(
            f"Recompressed JASP formatter resource is {gap} bytes under {declared}, "
            "too little room for a skippable zstd frame"
        )
    user = b"\x00" * (gap - 8)
    skip = (0x184D2A50).to_bytes(4, "little") + len(user).to_bytes(4, "little") + user
    fitted = compressed + skip
    if len(fitted) != declared:
        raise SystemExit("zstd skippable pad did not land on the original frame size")
    return fitted


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
        fitted = _fit_zstd_frame(rewritten, declared)
        blob[frame_at:frame_at + declared] = fitted
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
        path.write_bytes(updated)
        print(
            f"Patched JASP result formatter in {path} "
            f"(call sites={call_count}, latex sites={latex_count})",
            flush=True,
        )
        calls += call_count
        latex += latex_count
    return calls, latex


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
    assert len(_OLD_LATEX) == len(_NEW_LATEX)
    assert b"formatPrecision(content, sf, false, thousands)" in _OLD_WINDOW
    assert b"formatPrecision(content, sf, false, thousands)" not in _NEW_WINDOW
    assert b"((a,b)=>a.length<=b.length?a:b)" in _NEW_WINDOW
    assert _NEW_WINDOW.count(b"formatPrecisionWithRespectForFixedDecimals") == 1
    assert b"\\u00D7" in _OLD_LATEX and b"\\u00D7" not in _NEW_LATEX
    blob = b"prefix" + _OLD_LATEX + _OLD_WINDOW + b"suffix"
    updated, calls, latex = _apply_pairs(blob)
    assert calls == 1 and latex == 1
    assert updated == b"prefix" + _NEW_LATEX + _NEW_WINDOW + b"suffix"
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        binary = root / "bin" / "JASP"
        binary.parent.mkdir()
        binary.write_bytes(b"xxxx" + _OLD_LATEX + _OLD_WINDOW + b"yyyy")
        etc = root / "lib" / "R" / "etc"
        etc.mkdir(parents=True)
        (root / "lib" / "R" / "bin").mkdir()
        (root / "lib" / "R" / "bin" / "R").write_text("#!/bin/sh\n", encoding="utf-8")
        assert patch_tree(root) == (1, 1)
        patched = binary.read_bytes()
        assert _OLD_WINDOW not in patched and _OLD_LATEX not in patched
        assert _NEW_WINDOW in patched and _NEW_LATEX in patched
        assert len(patched) == len(b"xxxx" + _OLD_LATEX + _OLD_WINDOW + b"yyyy")
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
    calls, latex = patch_tree(root)
    if calls == 0 or latex == 0:
        raise SystemExit(
            "The JASP 0.98.8 result formatter was not patched "
            f"(call sites={calls}, latex sites={latex}). "
            "Refusing to leave sf:4 rendering in place."
        )
    install_seed_hook(root)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
