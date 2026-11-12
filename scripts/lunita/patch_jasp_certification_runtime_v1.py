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

Death Penalty.jasp stores seed 1 with setSeed false. Upstream JASP correctly
honors that checkbox, so the independent certification lane requests a
deterministic seed only through an explicit Flatpak environment flag. Normal
JASP launches retain the original checkbox behavior. The Rprofile.site hook
records a hash-bound execution marker so the lane proves that the real JASP R
runtime loaded the profile and applied seed 1. Fixture bytes and the comparator
are not modified.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
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
        certification_seed <- identical(
          Sys.getenv("LUNITA_JASP_CERTIFICATION_DETERMINISTIC_SEED"), "1"
        )
        if (isTRUE(options[["setSeed"]]) || certification_seed) {
          seed <- options[["seed"]]
          if (!is.numeric(seed) || length(seed) != 1L || !is.finite(seed))
            stop("LUNITA_JASP_SEED_INVALID")
          set.seed(as.integer(seed))
          receipt <- Sys.getenv("LUNITA_JASP_SEED_HOOK_RECEIPT", "")
          if (nzchar(receipt)) {
            cat(
              paste("SEED_APPLIED", Sys.getpid(), as.integer(seed),
                    if (isTRUE(options[["setSeed"]])) "TRUE" else "FALSE",
                    sep = "\t"),
              "\n", file = receipt, append = TRUE
            )
          }
        }
      }
      invisible(NULL)
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
        path.write_bytes(updated)
        print(
            f"Patched JASP result formatter in {path} "
            f"(call sites={call_count}, latex sites={latex_count})",
            flush=True,
        )
        calls += call_count
        latex += latex_count
    return calls, latex


def _is_r_home(path: pathlib.Path) -> bool:
    return (
        (path / "bin" / "R").is_file()
        and (path / "etc" / "Makeconf").is_file()
        and (path / "etc" / "Renviron").is_file()
        and (path / "library" / "base").is_dir()
    )


def _discover_r_home(root: pathlib.Path) -> pathlib.Path:
    root = root.resolve(strict=True)
    candidates: set[pathlib.Path] = set()
    for launcher in root.rglob("bin/R"):
        if not launcher.is_file():
            continue
        possible_homes = (launcher.parent.parent, launcher.resolve().parent.parent)
        for possible in possible_homes:
            try:
                home = possible.resolve(strict=True)
            except OSError:
                continue
            if not home.is_relative_to(root):
                continue
            if _is_r_home(home):
                candidates.add(home)
    ordered = sorted(candidates, key=lambda path: path.as_posix())
    if len(ordered) != 1:
        raise SystemExit(
            "Expected exactly one complete JASP R_HOME with bin/R, etc/Makeconf, "
            f"etc/Renviron and library/base under {root}; found {len(ordered)}: "
            + ", ".join(path.as_posix() for path in ordered)
        )
    return ordered[0]


def install_seed_hook(root: pathlib.Path) -> pathlib.Path:
    rhome = _discover_r_home(root)
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
    print(f"JASP_R_HOME={rhome}", flush=True)
    print(f"JASP_RPROFILE_SITE={site}", flush=True)
    print(f"JASP_RPROFILE_SITE_SHA256={__import__('hashlib').sha256(site.read_bytes()).hexdigest()}", flush=True)
    return site

def self_test() -> None:
    assert len(_OLD_WINDOW) == len(_NEW_WINDOW)
    assert len(_OLD_LATEX) == len(_NEW_LATEX)
    assert b"formatPrecision(content, sf, false, thousands)" in _OLD_WINDOW
    assert b"formatPrecision(content, sf, false, thousands)" not in _NEW_WINDOW
    assert b"((a,b)=>a.length<=b.length?a:b)" in _NEW_WINDOW
    assert _NEW_WINDOW.count(b"formatPrecisionWithRespectForFixedDecimals") == 1
    assert b"\u00D7" in _OLD_LATEX and b"\u00D7" not in _NEW_LATEX
    assert 'LUNITA_JASP_CERTIFICATION_DETERMINISTIC_SEED' in _SEED_HOOK
    assert 'LUNITA_JASP_SEED_HOOK_RECEIPT' in _SEED_HOOK
    assert 'if (isTRUE(options[["setSeed"]]) || certification_seed)' in _SEED_HOOK
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        binary = root / "bin" / "JASP"
        binary.parent.mkdir()
        binary.write_bytes(b"xxxx" + _OLD_LATEX + _OLD_WINDOW + b"yyyy")

        # The Flatpak app ships a wrapper at <files>/bin/R. Its parent is not
        # R_HOME; the complete installation is <files>/lib64/R.
        (root / "bin" / "R").write_text("#!/bin/sh\n", encoding="utf-8")
        (root / "etc").mkdir()
        actual = root / "lib64" / "R"
        (actual / "etc").mkdir(parents=True)
        (actual / "etc" / "Makeconf").write_text("R_HOME signature\n", encoding="utf-8")
        (actual / "etc" / "Renviron").write_text("R_HOME signature\n", encoding="utf-8")
        (actual / "library" / "base").mkdir(parents=True)
        (actual / "bin").mkdir(parents=True)
        (actual / "bin" / "R").write_text("#!/bin/sh\n", encoding="utf-8")

        assert patch_tree(root) == (1, 1)
        patched = binary.read_bytes()
        assert _OLD_WINDOW not in patched and _OLD_LATEX not in patched
        assert _NEW_WINDOW in patched and _NEW_LATEX in patched
        assert len(patched) == len(b"xxxx" + _OLD_LATEX + _OLD_WINDOW + b"yyyy")
        assert _discover_r_home(root) == actual.resolve()
        site = install_seed_hook(root)
        assert site == actual / "etc" / "Rprofile.site"
        assert not (root / "etc" / "Rprofile.site").exists()
        first = site.read_text(encoding="utf-8")
        assert first.count(_HOOK_MARK) == 2
        install_seed_hook(root)
        assert site.read_text(encoding="utf-8") == first

    # A wrapper without a complete R_HOME must fail closed.
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "bin").mkdir()
        (root / "bin" / "R").write_text("#!/bin/sh\n", encoding="utf-8")
        (root / "etc").mkdir()
        try:
            _discover_r_home(root)
        except SystemExit:
            pass
        else:
            raise AssertionError("R_HOME discovery accepted a wrapper-only decoy")

    # Two complete installations are ambiguous and must not be selected by traversal order.
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for name in ("lib64/R", "opt/R"):
            home = root / name
            (home / "etc").mkdir(parents=True)
            (home / "etc" / "Makeconf").write_text("R_HOME signature\n", encoding="utf-8")
            (home / "etc" / "Renviron").write_text("R_HOME signature\n", encoding="utf-8")
            (home / "library" / "base").mkdir(parents=True)
            (home / "bin").mkdir(parents=True)
            (home / "bin" / "R").write_text("#!/bin/sh\n", encoding="utf-8")
        try:
            _discover_r_home(root)
        except SystemExit:
            pass
        else:
            raise AssertionError("R_HOME discovery silently selected an ambiguous installation")
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
