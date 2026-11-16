"""Hard size gate. The limit applies to final SquashFS bytes, not estimates.

A required high-entropy payload whose admitted lower bound already exceeds
the residual budget blocks the build. Compression credit is zero unless a
measured SquashFS delta is supplied for that exact payload.
"""

from __future__ import annotations

HARD_MAX_BYTES = 515_000_000

# HEAD https://huggingface.co/bartowski/Qwen_Qwen3-0.6B-GGUF/resolve/main/Qwen_Qwen3-0.6B-IQ3_XS.gguf
# observed 2026-11-16: content-length and x-linked-size. Not a local SHA-256.
GGUF_CONTENT_LENGTH_BYTES = 379_605_408
GGUF_SHA256_CLAIM = "0906dcf62aa4f005887e855731376f0bf3be8f5ffa61f547df71e6154ea748d9"

# Flathub catalog page for org.jamovi.jamovi stated "436 MiB Download"
# on 2026-11-16. Not byte-measured and not hash-verified here.
JAMOVI_CATALOG_DOWNLOAD_BYTES = 436 * 1024 * 1024


def residual_after_gguf() -> int:
    return HARD_MAX_BYTES - GGUF_CONTENT_LENGTH_BYTES


def evaluate(payloads: list[dict]) -> dict:
    """payloads: id, lower_bound_bytes, required, epistemic, compression_credit_bytes."""
    accounted = 0
    rows = []
    for item in payloads:
        credit = int(item.get("compression_credit_bytes") or 0)
        if credit < 0:
            raise ValueError("NEGATIVE_COMPRESSION_CREDIT")
        if credit and item.get("compression_evidence") != "MEASURED_SQUASHFS_DELTA":
            raise ValueError("COMPRESSION_CREDIT_WITHOUT_MEASURED_DELTA")
        lower = int(item["lower_bound_bytes"])
        if lower < 0:
            raise ValueError("NEGATIVE_LOWER_BOUND")
        net = lower - credit
        if item.get("required"):
            accounted += net
        rows.append({**item, "net_lower_bound_bytes": net})
    blocked = accounted > HARD_MAX_BYTES
    return {
        "schema": "LUNITA_META28_SIZE_GATE/1.0",
        "hard_max_bytes": HARD_MAX_BYTES,
        "accounted_required_lower_bound_bytes": accounted,
        "over_by_bytes": max(0, accounted - HARD_MAX_BYTES),
        "final_squashfs_bytes": None,
        "status": "BUILD_BLOCKED_BY_SIZE_CONSTRAINT" if blocked else "SIZE_LOWER_BOUND_WITHIN_CAP",
        "note": "A within-cap lower bound is not a measured image and is not certification.",
        "payloads": rows,
    }


def meta28_default_payloads() -> list[dict]:
    return [
        {
            "id": "Qwen3-0.6B-IQ3_XS.gguf",
            "lower_bound_bytes": GGUF_CONTENT_LENGTH_BYTES,
            "required": True,
            "epistemic": "REMOTE_CONTENT_LENGTH",
            "sha256_claim": GGUF_SHA256_CLAIM,
            "locally_hashed": False,
            "compression_credit_bytes": 0,
        },
        {
            "id": "org.jamovi.jamovi",
            "lower_bound_bytes": JAMOVI_CATALOG_DOWNLOAD_BYTES,
            "required": True,
            "epistemic": "RETRIEVED_CATALOG_CLAIM",
            "source": "https://flathub.org/en/apps/org.jamovi.jamovi",
            "catalog_text": "436 MiB Download",
            "locally_hashed": False,
            "compression_credit_bytes": 0,
        },
    ]
