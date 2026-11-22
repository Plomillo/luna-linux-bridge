#!/usr/bin/env python3
"""Independent check. Recomputes case results from raw outputs. Ignores Luna's pass bit."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REF_DEB = "fa372953f47c61019202995754cec7d688adf973c4491218e3b4db2465163657"
REF_SH = "d74a0b5eefeba4a5777c87b97008169a540aee25861fb883f0943379cf7db8f7"
REF_TREE = "69268df2839d88b25ae75060b3c9da7dc6aef710128bfb587a7b1ebc19b9c322"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def judge(case: dict) -> bool:
    kind = case.get("expect")
    code = case.get("code")
    out = case.get("stdout") or ""
    if kind == "code0":
        return code == 0
    if kind == "code_eq":
        return code == case.get("expect_code")
    if kind == "stdout_contains":
        return code == 0 and case.get("needle", "") in out
    if kind == "stdout_eq":
        return code == 0 and out.strip() == case.get("needle", "")
    if kind == "any_line_eq":
        return code == 0 and case.get("needle", "") in {line.strip() for line in out.splitlines()}
    if kind == "json_selftest":
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return False
        return code == 0 and data.get("ok") is True and data.get("certification") == "NOT_CERTIFIED"
    if kind == "json_luna":
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return False
        return (
            code == 0
            and data.get("weight_training") == "NOT_AUTHORIZED"
            and data.get("consciousness") == "NOT_CLAIMED"
            and data.get("product_platform") == "NOT_CERTIFIED"
            and data.get("self_certifies") is False
        )
    return False


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "evidence")
    failures = []
    deb = root / "artifacts" / "LOUKSNA.deb"
    sh = root / "artifacts" / "LOUKSNA.sh"
    hashes = {}
    if deb.is_file():
        hashes["deb"] = sha256(deb)
        if hashes["deb"] != REF_DEB:
            failures.append("DEB_HASH")
    else:
        failures.append("DEB_ABSENT")
    if sh.is_file():
        hashes["sh"] = sha256(sh)
        if hashes["sh"] != REF_SH:
            failures.append("SH_HASH")
    else:
        failures.append("SH_ABSENT")
    sums = root / "artifacts" / "SHA256SUMS"
    if sums.is_file() and REF_TREE not in sums.read_text():
        failures.append("TREE_LINE_ABSENT")
    boot = root / "vm" / "boot.log"
    if not boot.is_file() or boot.stat().st_size < 200:
        failures.append("BOOT_LOG_ABSENT")
    version = root / "vm" / "debian-version.txt"
    version_text = version.read_text() if version.is_file() else ""
    if 'VERSION_ID="13"' not in version_text and "VERSION_ID=13" not in version_text:
        failures.append("DEBIAN_13_NOT_PROVEN")
    pid1 = (root / "vm" / "pid1.txt").read_text().strip() if (root / "vm" / "pid1.txt").is_file() else ""
    if pid1 != "systemd":
        failures.append("SYSTEMD_PID1_NOT_PROVEN")
    kvm = {}
    kvm_path = root / "vm" / "vm-capabilities.json"
    if kvm_path.is_file():
        kvm = json.loads(kvm_path.read_text())
    cases_path = root / "luna" / "agent-53-case-execution.json"
    spec = json.loads(Path(__file__).with_name("expectations.json").read_text())
    recomputed = []
    if not cases_path.is_file():
        failures.append("LUNA_CASES_ABSENT")
    else:
        cases = json.loads(cases_path.read_text())
        if len(cases) != 53 or len(spec) != 53:
            failures.append(f"LUNA_CASE_COUNT_{len(cases)}_{len(spec)}")
        by_id = {row.get("id"): row for row in cases}
        for item in spec:
            case = by_id.get(item["id"])
            if case is None:
                failures.append(f"MISSING_{item['id']}")
                continue
            merged = dict(case)
            merged["expect"] = item["expect"]
            merged["needle"] = item.get("needle", "")
            merged["expect_code"] = item.get("expect_code")
            ok = judge(merged)
            recomputed.append({"id": item["id"], "g23_pass": ok, "luna_pass": case.get("pass")})
            if not ok:
                failures.append(f"CASE_{item['id']}")
            if case.get("pass") is True and not ok:
                failures.append(f"LUNA_OVERCLAIM_{item['id']}")
    historical = root / "historical" / "tests-36-audit.json"
    if not historical.is_file():
        failures.append("HISTORICAL_AUDIT_ABSENT")
    else:
        hist = json.loads(historical.read_text())
        if hist.get("reexecuted") != 0:
            failures.append("HISTORICAL_REEXECUTED")
        if hist.get("individually_verified") != 36:
            failures.append("HISTORICAL_INDIVIDUAL_EVIDENCE_INCOMPLETE")
    original = root / "cases" / "original-803-audit.json"
    if not original.is_file():
        failures.append("ORIGINAL_803_AUDIT_ABSENT")
    else:
        audit = json.loads(original.read_text())
        if audit.get("reexecuted") != 0:
            failures.append("ORIGINAL_803_REEXECUTED")
        if audit.get("individually_verified") != 803:
            failures.append("ORIGINAL_803_INDIVIDUAL_EVIDENCE_INCOMPLETE")
    recovery = root / "cases" / "original-53-recovery.json"
    if not recovery.is_file():
        failures.append("ORIGINAL_53_SEARCH_ABSENT")
    wayland = (root / "vm" / "wayland-checks.txt").read_text() if (root / "vm" / "wayland-checks.txt").is_file() else ""
    if "WAYLAND_SOCKET=yes" not in wayland or "KWIN=yes" not in wayland or "PLASMA=yes" not in wayland:
        failures.append("KDE_WAYLAND_SESSION_NOT_PROVEN")
    audio = (root / "vm" / "audio-checks.txt").read_text() if (root / "vm" / "audio-checks.txt").is_file() else ""
    if "SND=yes" not in audio or "PACTL=yes" not in audio:
        failures.append("AUDIO_NOT_PROVEN")
    verdict = "PASS" if not failures else "FAIL"
    out = {
        "producer": "louksna-g23-debian13",
        "verdict": verdict,
        "failures": failures,
        "hashes": hashes,
        "kvm": kvm.get("kvm"),
        "accel": kvm.get("accel"),
        "recomputed_failures": [row["id"] for row in recomputed if not row["g23_pass"]],
        "product_platform": "NOT_CERTIFIED" if verdict != "PASS" else "SEE_G24",
    }
    dest = root / "certification" / "independent-validation.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"verdict": verdict, "failure_count": len(failures)}, indent=2))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
