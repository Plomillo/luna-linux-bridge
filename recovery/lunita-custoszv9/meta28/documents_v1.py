"""Document compatibility is a measured chain, not a file extension."""

from __future__ import annotations

CHAIN = (
    "DECLARED",
    "IMPLEMENTED",
    "OPEN_TESTED",
    "EDIT_TESTED",
    "SAVE_TESTED",
    "REOPEN_TESTED",
    "EXPORT_TESTED",
)

FORMATS = ("ODT", "DOCX", "RTF", "TXT", "PDF", "HTML", "ODS", "XLSX", "CSV", "TSV", "ODP", "PPTX")


def compatibility(fmt: str, reached: str) -> dict:
    if fmt not in FORMATS:
        return {"format": fmt, "status": "UNSUPPORTED", "compatible": False}
    if reached not in CHAIN:
        return {"format": fmt, "status": "INVALID_STAGE", "compatible": False}
    index = CHAIN.index(reached)
    compatible = index == len(CHAIN) - 1
    return {
        "format": fmt,
        "reached": reached,
        "compatible": compatible,
        "status": "EXPORT_TESTED" if compatible else "NOT_COMPATIBLE",
    }
