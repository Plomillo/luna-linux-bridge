#!/usr/bin/env python3
"""Conservative, evidenced pruning of an isolated official Calibre install tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone

ALLOWED_CONVERSION_MODULES = {
    "__init__.py", "archive_input.py",
    "pdf_input.py", "pdf_output.py",
    "epub_input.py", "epub_output.py",
    "html_input.py", "txt_input.py",
    "docx_input.py", "odt_input.py", "rtf_input.py",
    "oeb_output.py",
}
ALLOWED_ENTRYPOINTS = {
    "calibre", "calibre-complete", "calibre-customize", "calibre-debug",
    "calibre-parallel", "calibre-server", "calibre-smtp", "calibredb",
    "ebook-device", "ebook-edit", "ebook-meta", "ebook-polish", "ebook-viewer",
    "fetch-ebook-metadata", "lrf2lrs", "lrs2lrf", "markdown-calibre", "web2disk",
}
KEEP_ROOT_ENTRYPOINTS = {
    "ebook-convert", "calibre-parallel", "calibre_postinstall", "calibre-uninstall",
}
KEEP_DEFAULT_COVERS = {
    "resources/images/default_cover.png",
    "resources/catalog/DefaultCover.jpg",
}
KEEP_RESOURCE_FILES = {
    "resources/default_tweaks.py",
    "resources/calibre-mimetypes.xml",
    "resources/common-english-words.txt",
    "resources/fonts/calibreSymbols.otf",
}
KEEP_WEBENGINE_LOCALES = {"en-US.pak", "es.pak", "es-419.pak", "es-MX.pak"}
LOCALE_NAME = re.compile(r"(?:^|[_-])([a-z]{2,3}(?:[-_][a-z0-9]{2,8})*)\.(?:qm|mo)$", re.IGNORECASE)
KEEP_LOCALES = {"en", "en-us", "en_us", "es", "es-es", "es_es", "es-419", "es_419", "es-mx", "es_mx"}
KNOWN_LANGUAGES = set("""
af am ar ast az be bg bn br bs ca cs cy da de el en eo es et eu fa fi fr fy ga gd gl gu he hi hr hu hy id is it ja ka kk km kn ko ku ky la lt lv mk ml mn mr ms my nb ne nl nn no oc pa pl pt ro ru sk sl sq sr sv sw ta te th tl tr tt ug uk ur uz vi wa xh zh
""".split())
KEEP_LANGUAGE_BASES = {"en", "es"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def in_conversion_plugins(rel: Path) -> bool:
    parts = rel.parts
    for index in range(len(parts) - 2):
        if parts[index:index + 3] == ("ebooks", "conversion", "plugins"):
            return True
    return False


def conversion_module_allowed(rel: Path) -> bool:
    parts = rel.parts
    index = None
    for i in range(len(parts) - 2):
        if parts[i:i + 3] == ("ebooks", "conversion", "plugins"):
            index = i + 3
            break
    if index is None:
        return True
    tail = parts[index:]
    if not tail:
        return True
    if tail[0] == "__pycache__":
        if len(tail) != 2:
            return True
        stem = tail[1].split(".", 1)[0]
        return f"{stem}.py" in ALLOWED_CONVERSION_MODULES
    if len(tail) == 1:
        name = tail[0]
        if name.endswith(".pyc"):
            return f"{name[:-4]}.py" in ALLOWED_CONVERSION_MODULES
        if name.endswith(".py") and (
            name.endswith("_input.py") or name.endswith("_output.py") or name == "__init__.py"
        ):
            return name in ALLOWED_CONVERSION_MODULES
    return True


def locale_base(token: str) -> str | None:
    value = token.strip().replace("_", "-").lower()
    for suffix in (".mo", ".qm", ".pak", ".json", ".txt", ".dat"):
        if value.endswith(suffix):
            value = value[:-len(suffix)]
            break
    if value in KNOWN_LANGUAGES:
        return value
    match = re.match(r"^([a-z]{2,3})(?:-[a-z0-9]{2,8})+$", value)
    if match and match.group(1) in KNOWN_LANGUAGES:
        return match.group(1)
    # Locale files can be named calibre-es.qm or calibre_de.mo.
    match = re.search(r"(?:^|[_-])([a-z]{2,3})(?:-[a-z0-9]{2,8})?$", value)
    if match and match.group(1) in KNOWN_LANGUAGES:
        return match.group(1)
    return None


def zip_entry_language(name: str) -> str | None:
    for token in PurePosixPath(name).parts:
        base = locale_base(token)
        if base:
            return base
    return None


def prune_locale_archive(root: Path) -> dict[str, object]:
    """Retain English and Spanish locale-specific entries inside Calibre's locale ZIP."""
    archive_path = root / "resources/localization/locales.zip"
    if not archive_path.is_file():
        return {"status": "NOT_PRESENT", "removed_entries": 0, "bytes_saved": 0}
    before_bytes = archive_path.stat().st_size
    with zipfile.ZipFile(archive_path, "r") as source:
        entries = source.infolist()
        decisions = []
        for info in entries:
            language = zip_entry_language(info.filename)
            remove = language is not None and language not in KEEP_LANGUAGE_BASES
            decisions.append((info, language, remove))
        removed = [
            {"path": info.filename, "language": language, "size_bytes": info.file_size}
            for info, language, remove in decisions if remove
        ]
        kept = [(info, language) for info, language, remove in decisions if not remove]

        # If we cannot positively identify any locale-specific entries, fail closed
        # and preserve the original archive.
        if not removed or not any(language in KEEP_LANGUAGE_BASES for _, language in kept):
            return {
                "status": "PRESERVED_NO_SAFE_LOCALE_CLASSIFICATION",
                "before_bytes": before_bytes,
                "after_bytes": before_bytes,
                "bytes_saved": 0,
                "entry_count_before": len(entries),
                "entry_count_after": len(entries),
                "removed_entries": 0,
                "samples": [info.filename for info in entries[:100]],
            }

        fd, temp_name = tempfile.mkstemp(prefix="calibre-locales-", suffix=".zip", dir=archive_path.parent)
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            with zipfile.ZipFile(temp_path, "w") as target:
                target.comment = source.comment
                for info, _language in kept:
                    target.writestr(info, source.read(info.filename))
            # Verify all retained entries are readable before replacing the original.
            with zipfile.ZipFile(temp_path, "r") as verify:
                corrupt = verify.testzip()
                if corrupt:
                    raise RuntimeError(f"Locale archive integrity check failed: {corrupt}")
            os.replace(temp_path, archive_path)
        finally:
            temp_path.unlink(missing_ok=True)

    after_bytes = archive_path.stat().st_size
    return {
        "status": "PRUNED_AND_VERIFIED",
        "before_bytes": before_bytes,
        "after_bytes": after_bytes,
        "bytes_saved": before_bytes - after_bytes,
        "entry_count_before": len(entries),
        "entry_count_after": len(kept),
        "removed_entries": len(removed),
        "removed_locale_payload_bytes": sum(item["size_bytes"] for item in removed),
        "removed_samples": removed[:100],
    }


def locale_should_remove(rel: Path) -> bool:
    name = rel.name
    if rel.suffix.lower() in {".qm", ".mo"}:
        match = LOCALE_NAME.search(name)
        if match:
            locale = match.group(1).lower().replace("_", "-")
            return locale not in KEEP_LOCALES
    if "qtwebengine_locales" in [part.lower() for part in rel.parts] and name.lower().endswith(".pak"):
        return name not in KEEP_WEBENGINE_LOCALES
    return False


def removal_reason(rel: Path) -> str | None:
    parts = rel.parts
    posix = rel.as_posix()

    if parts and parts[0] in {"recipes", "manual", "icons"}:
        return "unused_root_feature_or_documentation"
    if len(parts) >= 2 and parts[0] == "resources":
        if posix in KEEP_RESOURCE_FILES:
            return None
        if posix == "resources/qtwebengine_devtools_resources.pak":
            return "unused_browser_developer_tools_resources"
        if parts[1] in {"content-server", "editor-help", "dictionaries", "manual", "recipes"}:
            return "unused_server_editor_spellcheck_or_news_resources"
        if parts[1] == "images" and posix not in KEEP_DEFAULT_COVERS:
            return "standalone_GUI_image_resource"
        if parts[1] == "catalog" and posix not in KEEP_DEFAULT_COVERS:
            return "catalog_creation_resource_not_in_scope"
        if posix in {
            "resources/calibre-portable.bat",
            "resources/calibre-portable.sh",
        }:
            return "unused_portable_resource"

    # Piper is Calibre's speech output subsystem; Cajita does not ship TTS.
    if posix.startswith("share/espeak-ng-data/"):
        return "unused_text_to_speech_language_payload"
    if posix.startswith("lib/") and re.fullmatch(r"libonnxruntime\.so(?:\..*)?", rel.name):
        return "unused_text_to_speech_onnxruntime_dependency"
    if posix.startswith("lib/calibre-extensions/") and rel.name.lower().startswith("piper"):
        return "unused_text_to_speech_native_extension"

    if len(parts) == 1 and rel.name in ALLOWED_ENTRYPOINTS and rel.name not in KEEP_ROOT_ENTRYPOINTS:
        return "unused_GUI_library_server_device_or_metadata_command"

    if locale_should_remove(rel):
        return "non_English_or_Spanish_UI_localization"

    if len(parts) == 1 and rel.name in KEEP_ROOT_ENTRYPOINTS:
        return None

    if in_conversion_plugins(rel) and not conversion_module_allowed(rel):
        return "conversion_plugin_format_outside_candidate_allowlist"

    return None


def measure(root: Path) -> tuple[int, int]:
    count = 0
    total = 0
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            count += 1
            total += path.stat().st_size
    return count, total


def largest_items(root: Path, limit: int = 25) -> list[dict[str, object]]:
    files = [
        (p.stat().st_size, p.relative_to(root).as_posix())
        for p in root.rglob("*")
        if p.is_file() and not p.is_symlink()
    ]
    return [
        {"path": rel, "size_bytes": size}
        for size, rel in sorted(files, reverse=True)[:limit]
    ]


def directory_totals(root: Path, limit: int = 25) -> list[dict[str, object]]:
    totals: dict[str, int] = {}
    for p in root.rglob("*"):
        if not p.is_file() or p.is_symlink():
            continue
        rel = p.relative_to(root)
        if len(rel.parts) > 1:
            top = rel.parts[0]
            totals[top] = totals.get(top, 0) + p.stat().st_size
    return [
        {"directory": name, "size_bytes": size}
        for name, size in sorted(totals.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]


def build_plan(root: Path) -> list[tuple[Path, str]]:
    plan: list[tuple[Path, str]] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root)
        reason = removal_reason(rel)
        if reason:
            plan.append((path, reason))
    return sorted(plan, key=lambda item: item[0].relative_to(root).as_posix())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Raíz aislada del Calibre oficial extraído.")
    parser.add_argument("--report", type=Path, required=True, help="JSON de archivos eliminados y tamaños.")
    parser.add_argument("--apply", action="store_true", help="Aplicar la poda; sin esta opción solo informa.")
    args = parser.parse_args(argv)

    root = args.root.expanduser().resolve()
    if not root.is_dir():
        parser.error("--root no es un directorio.")
    if root == Path("/") or root in {Path("/usr"), Path("/opt"), Path("/usr/local"), Path.home()}:
        parser.error("Se rechazó una raíz demasiado amplia o de instalación del sistema.")
    if not (root / "ebook-convert").exists():
        parser.error("No parece una raíz de Calibre: falta ebook-convert en la raíz.")
    if not (root / "calibre_postinstall").exists():
        parser.error("No se reconoce el paquete binario oficial: falta calibre_postinstall.")

    before_count, before_bytes = measure(root)
    plan = build_plan(root)
    removals = []
    for path, reason in plan:
        rel = path.relative_to(root).as_posix()
        removals.append({
            "path": rel,
            "reason": reason,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })

    locale_archive_report: dict[str, object] = {"status": "DRY_RUN_NOT_APPLIED"}
    if args.apply:
        for path, _reason in plan:
            path.unlink(missing_ok=True)
        locale_archive_report = prune_locale_archive(root)
        for directory in sorted(
            (p for p in root.rglob("*") if p.is_dir() and not p.is_symlink()),
            key=lambda p: len(p.parts),
            reverse=True,
        ):
            try:
                directory.rmdir()
            except OSError:
                pass
        required = [
            root / "ebook-convert",
            root / "calibre-parallel",
            root / "calibre_postinstall",
            root / "resources/default_tweaks.py",
            root / "resources/calibre-mimetypes.xml",
        ]
        missing = [str(p.relative_to(root)) for p in required if not p.is_file()]
        if missing:
            print(f"FAIL_CLOSED: faltan archivos de conversión requeridos: {missing}", file=sys.stderr)
            return 3
        after_count, after_bytes = measure(root)
        removed_bytes = before_bytes - after_bytes
    else:
        after_count, after_bytes, removed_bytes = before_count, before_bytes, 0

    report = {
        "schema": "CAJITA_CALIBRE_PRUNE_REPORT/1.0",
        "created_at_utc": utc_now(),
        "candidate_version": "CAJITA_CALIBRE_COMPACT_V1_LINUX_X86_64",
        "root": str(root),
        "mode": "APPLIED" if args.apply else "DRY_RUN",
        "before": {"file_count": before_count, "bytes": before_bytes},
        "planned_removals": len(removals),
        "planned_removed_bytes": sum(item["size_bytes"] for item in removals),
        "after": {"file_count": after_count, "bytes": after_bytes},
        "measured_removed_bytes": removed_bytes,
        "locale_archive": locale_archive_report,
        "largest_remaining_files": largest_items(root),
        "largest_top_level_directories": directory_totals(root),
        "retained_conversion_modules": sorted(ALLOWED_CONVERSION_MODULES),
        "removed_files": removals,
        "status": "PRUNE_APPLIED_AWAITING_FUNCTIONAL_TESTS" if args.apply else "DRY_RUN_ONLY",
        "certification": "NOT_GRANTED",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "mode": report["mode"],
        "before_bytes": before_bytes,
        "after_bytes": after_bytes,
        "measured_removed_bytes": removed_bytes,
        "files_removed": len(removals),
        "locale_archive": locale_archive_report,
        "largest_remaining_files": report["largest_remaining_files"][:15],
        "largest_top_level_directories": report["largest_top_level_directories"][:15],
        "report": str(args.report),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
