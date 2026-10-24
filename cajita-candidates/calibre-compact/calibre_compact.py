#!/usr/bin/env python3
"""Governed CLI wrapper for the Cajita Calibre Compact candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any

CANDIDATE_VERSION = "1.0.0"
UPSTREAM_VERSION = os.environ.get("CALIBRE_UPSTREAM_VERSION", "9.17.0")

ALLOWED_INPUTS = {
    ".pdf", ".epub", ".html", ".htm", ".xhtml", ".xhtm", ".shtml", ".shtm",
    ".txt", ".text", ".md", ".markdown", ".docx", ".docm", ".odt", ".rtf",
}
ALLOWED_OUTPUTS = {".pdf", ".epub"}


class CandidateError(Exception):
    """Expected fail-closed candidate error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_format_pair(input_path: Path, output_path: Path) -> None:
    input_ext = input_path.suffix.lower()
    output_ext = output_path.suffix.lower()
    if input_ext not in ALLOWED_INPUTS:
        raise CandidateError(
            f"Formato de entrada no admitido: {input_ext or '(sin extensión)'}. "
            f"Admitidos: {', '.join(sorted(ALLOWED_INPUTS))}"
        )
    if output_ext not in ALLOWED_OUTPUTS:
        raise CandidateError(
            f"Formato de salida no admitido: {output_ext or '(sin extensión)'}. "
            "Solo se permiten .pdf y .epub."
        )
    if input_ext == output_ext:
        raise CandidateError(
            "La entrada y la salida tienen el mismo formato; este candidato solo "
            "expone conversiones hacia PDF o EPUB desde un formato distinto."
        )


def validate_pdf(path: Path) -> None:
    with path.open("rb") as stream:
        signature = stream.read(5)
    if signature != b"%PDF-":
        raise CandidateError("El resultado no contiene una cabecera PDF válida.")
    if path.stat().st_size < 100:
        raise CandidateError("El PDF resultante es anormalmente pequeño.")


def validate_epub(path: Path) -> None:
    if not zipfile.is_zipfile(path):
        raise CandidateError("El resultado EPUB no es un contenedor ZIP válido.")
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if not names or names[0] != "mimetype":
                raise CandidateError("EPUB inválido: 'mimetype' no es la primera entrada.")
            info = archive.getinfo("mimetype")
            if info.compress_type != zipfile.ZIP_STORED:
                raise CandidateError("EPUB inválido: 'mimetype' debe ir sin compresión.")
            if archive.read("mimetype") != b"application/epub+zip":
                raise CandidateError("EPUB inválido: contenido MIME incorrecto.")
            if "META-INF/container.xml" not in names:
                raise CandidateError("EPUB inválido: falta META-INF/container.xml.")
            if not any(name.lower().endswith(".opf") for name in names):
                raise CandidateError("EPUB inválido: no se encuentra paquete OPF.")
            corrupt_member = archive.testzip()
            if corrupt_member:
                raise CandidateError(f"EPUB corrupto en la entrada {corrupt_member!r}.")
    except zipfile.BadZipFile as exc:
        raise CandidateError(f"El EPUB resultante está dañado: {exc}") from exc
    if path.stat().st_size < 100:
        raise CandidateError("El EPUB resultante es anormalmente pequeño.")


def validate_output(path: Path, extension: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise CandidateError("El motor no produjo un archivo regular de salida.")
    if path.stat().st_size == 0:
        raise CandidateError("El motor produjo un archivo vacío.")
    if extension == ".pdf":
        validate_pdf(path)
    elif extension == ".epub":
        validate_epub(path)
    else:
        raise CandidateError(f"Validador no implementado para {extension!r}.")


def find_converter() -> str:
    configured = os.environ.get("CALIBRE_EBOOK_CONVERT")
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate.resolve())
        raise CandidateError("CALIBRE_EBOOK_CONVERT no apunta a un ejecutable válido.")
    found = shutil.which("ebook-convert")
    if found:
        return found
    raise CandidateError(
        "No se encontró ebook-convert. Define CALIBRE_EBOOK_CONVERT con la ruta "
        "del motor verificado."
    )


def default_audit_path() -> Path:
    override = os.environ.get("CALIBRE_COMPACT_AUDIT_LOG")
    if override:
        return Path(override).expanduser()
    state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return state_home / "cajita" / "calibre-compact" / "audit.jsonl"


def append_audit(path: Path, record: dict[str, Any]) -> None:
    """Append one JSONL record and flush it to stable storage."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)


def run_conversion(
    input_file: Path,
    output_file: Path,
    *,
    force: bool = False,
    timeout_seconds: int = 600,
    audit_path: Path | None = None,
) -> dict[str, Any]:
    validate_format_pair(input_file, output_file)
    source = input_file.expanduser().resolve(strict=True)
    if not source.is_file():
        raise CandidateError("La entrada no es un archivo regular.")
    target = output_file.expanduser().absolute()
    target.parent.mkdir(parents=True, exist_ok=True)
    if source == target.resolve(strict=False):
        raise CandidateError("La ruta de entrada y salida no pueden coincidir.")
    if target.is_symlink():
        raise CandidateError("No se sobrescriben enlaces simbólicos de salida.")
    if target.exists() and not force:
        raise CandidateError("La salida ya existe; usa --force para reemplazarla.")
    if target.exists() and not target.is_file():
        raise CandidateError("La ruta de salida existente no es un archivo regular.")
    if not 1 <= timeout_seconds <= 3600:
        raise CandidateError("El timeout debe estar entre 1 y 3600 segundos.")

    converter = find_converter()
    log_path = audit_path or default_audit_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab"):
        pass

    operation_id = str(uuid.uuid4())
    started_at = utc_now()
    start = time.monotonic()
    input_size = source.stat().st_size
    input_hash = sha256_file(source)
    staged = target.with_name(f".{target.stem}.cajita-stage-{operation_id}{target.suffix}")
    backup: Path | None = None
    base_record: dict[str, Any] = {
        "schema": "CAJITA_CALIBRE_CONVERSION_EVENT/1.0",
        "operation_id": operation_id,
        "candidate_version": CANDIDATE_VERSION,
        "upstream_version": UPSTREAM_VERSION,
        "started_at_utc": started_at,
        "input_path": str(source),
        "input_bytes": input_size,
        "input_sha256": input_hash,
        "output_path": str(target),
        "input_format": source.suffix.lower().lstrip("."),
        "output_format": target.suffix.lower().lstrip("."),
        "converter": converter,
        "timeout_seconds": timeout_seconds,
    }

    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
    env.setdefault("LANG", "C.UTF-8")
    env.setdefault("LC_ALL", "C.UTF-8")
    config_home = Path(
        os.environ.get("CALIBRE_COMPACT_CONFIG_DIR", Path.home() / ".config/cajita/calibre-compact")
    ).expanduser()
    config_home.mkdir(parents=True, exist_ok=True)
    env["CALIBRE_CONFIG_DIRECTORY"] = str(config_home)

    try:
        result = subprocess.run(
            [converter, str(source), str(staged)],
            shell=False,
            check=False,
            timeout=timeout_seconds,
            env=env,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            raise CandidateError(f"ebook-convert terminó con código {result.returncode}.")
        validate_output(staged, target.suffix.lower())
        output_hash = sha256_file(staged)
        output_size = staged.stat().st_size

        if target.exists():
            backup = target.with_name(f".{target.name}.cajita-backup-{operation_id}")
            os.replace(target, backup)
        os.replace(staged, target)

        record = {
            **base_record,
            "finished_at_utc": utc_now(),
            "elapsed_seconds": round(time.monotonic() - start, 6),
            "output_bytes": output_size,
            "output_sha256": output_hash,
            "return_code": 0,
            "status": "COMMITTED_AND_VALIDATED",
        }
        try:
            append_audit(log_path, record)
        except Exception:
            target.unlink(missing_ok=True)
            if backup is not None and backup.exists():
                os.replace(backup, target)
                backup = None
            raise CandidateError("No se pudo registrar la evidencia; se revirtió la salida.")
        if backup is not None:
            backup.unlink(missing_ok=True)
        return record

    except subprocess.TimeoutExpired as exc:
        staged.unlink(missing_ok=True)
        record = {
            **base_record, "finished_at_utc": utc_now(),
            "elapsed_seconds": round(time.monotonic() - start, 6),
            "status": "FAILED_TIMEOUT", "error": str(exc),
        }
        append_audit(log_path, record)
        raise CandidateError(f"Conversión detenida por timeout ({timeout_seconds}s).") from exc
    except Exception as exc:
        staged.unlink(missing_ok=True)
        if backup is not None and backup.exists() and not target.exists():
            os.replace(backup, target)
        if isinstance(exc, CandidateError):
            error = str(exc)
        else:
            error = f"{type(exc).__name__}: {exc}"
        record = {
            **base_record, "finished_at_utc": utc_now(),
            "elapsed_seconds": round(time.monotonic() - start, 6),
            "status": "FAILED", "error": error,
        }
        try:
            append_audit(log_path, record)
        except Exception:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Conversión documental gobernada con Calibre: salida únicamente PDF o EPUB."
    )
    parser.add_argument("input", nargs="?", help="Archivo de entrada admitido.")
    parser.add_argument("output", nargs="?", help="Archivo de salida .pdf o .epub.")
    parser.add_argument("--force", action="store_true", help="Reemplazar una salida existente tras validar la nueva.")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout de conversión en segundos (1–3600).")
    parser.add_argument("--audit-log", type=Path, help="Ruta del registro JSONL append-only.")
    parser.add_argument("--version", action="version", version=f"Cajita Calibre Compact {CANDIDATE_VERSION}; Calibre {UPSTREAM_VERSION}")
    args = parser.parse_args(argv)
    if not args.input or not args.output:
        parser.error("debes especificar archivo de entrada y salida.")

    try:
        record = run_conversion(
            Path(args.input),
            Path(args.output),
            force=args.force,
            timeout_seconds=args.timeout,
            audit_path=args.audit_log,
        )
        print(json.dumps({
            "status": record["status"],
            "operation_id": record["operation_id"],
            "output": record["output_path"],
            "output_bytes": record["output_bytes"],
            "output_sha256": record["output_sha256"],
        }, ensure_ascii=False))
        return 0
    except (CandidateError, OSError) as exc:
        print(f"calibre-compact: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
