#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib

path = pathlib.Path("tcp-endpoint-telemetry.jsonl")
rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
if not rows or rows[0].get("event") != "startup":
    raise SystemExit("TELEMETRY_STARTUP_MISSING")
previous = "0" * 64
max_rss = 0
for row in rows:
    if row.get("prev_hash") != previous:
        raise SystemExit("HASH_CHAIN_PREV_MISMATCH")
    entry_hash = row.get("entry_hash")
    if not isinstance(entry_hash, str):
        raise SystemExit("HASH_CHAIN_ENTRY_MISSING")
    record = dict(row)
    del record["entry_hash"]
    calculated = hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if calculated != entry_hash:
        raise SystemExit("HASH_CHAIN_INVALID")
    previous = entry_hash
    max_rss = max(max_rss, int(row["rss_bytes"]))
print("TELEMETRY_ROWS", len(rows))
print("PEAK_RSS_BYTES", max_rss)
print("PEAK_RSS_MIB", round(max_rss / 1024 / 1024, 3))
print("BUDGET_BYTES", 1024 * 1024 * 1024)
print("BUDGET_STATUS", "WITHIN_BUDGET" if max_rss <= 1024 * 1024 * 1024 else "OVER_BUDGET")
if max_rss > 1024 * 1024 * 1024:
    raise SystemExit(3)
