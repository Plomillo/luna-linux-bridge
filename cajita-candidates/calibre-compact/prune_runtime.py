#!/usr/bin/env python3
"""Conservative, evidenced pruning of an isolated official Calibre install tree."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
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
KEEP_ROOT_ENTRYPOINTS = {"ebook-convert", "calibre_postinstall", "calibre-uninstall"}
KEEP_DEFAULT_COVERS = {
    "resources/images/default_cover.png",
    "resources/catalog/DefaultCover.jpg",
}
KEEP_WEBENGINE_LOCALES = {"en-US.pak", "es.pak", "es-419.pak", "es-MX.pak"}
LOCALE_NAME = re.compile(r"(?:^|[_-])([a-z]{2,3}(?:[-_][a-z0-9]{2,8})*)\.(?:qm|mo)$", re.IGNORECASE)
KEEP_LOCALES = {"en", "en-us", "en_us", "es", "es-es", "es_es", "es-419", "es_419", "es-mx", "es_mx"}


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
        if parts[1] in {"content-server", "editor-help", "dictionaries", "manual", "recipes"}:
            return "unused_server_editor_spellcheck_or_news_resources"
        if parts[1] == "images" and posix not in KEEP_DEFAULT_COVERS:
            return "standalone_GUI_image_resource"
        if parts[1] == "catalog" and posix not in KEEP_DEFAULT_COVERS:
            return "catalog_creation_resource_not_in_scope"
        if posix in {
            "resources/calibre-portable.bat",
            "resources/calibre-portable.sh",
            "resources/default_tweaks.py",
        }:
            return "unused_portable_or_GUI_customization_resource"

    if len(parts) == 1 and rel.name in ALLOWED_ENTRYPOINTS:
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

    if args.apply:
        for path, _reason in plan:
            path.unlink(missing_ok=True)
        for directory in sorted(
            (p for p in root.rglob("*") if p.is_dir() and not p.is_symlink()),
            key=lambda p: len(p.parts),
            reverse=True,
        ):
            try:
                directory.rmdir()
            except OSError:
                pass
        if not (root / "ebook-convert").is_file() or not (root / "calibre_postinstall").is_file():
            print("FAIL_CLOSED: los entrypoints básicos desaparecieron durante la poda.", file=sys.stderr)
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
        "report": str(args.report),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
