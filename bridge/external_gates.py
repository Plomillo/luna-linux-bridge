#!/usr/bin/env python3
"""Verify externally signed, scope-bound G23/G24 receipts; never issue them.

Owner and G23/G24 keys must be provisioned OUTSIDE the repository under an
owner-approved root-controlled trust directory. Signature validity is not a
substitute for independence review or for the material executor's single-use
authorization consumption.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

import lrb_core as base

SCHEMA = "LRB_EXTERNAL_GATE_VERIFICATION/0.3"
ROLES = ("OWNER", "G23", "G24", "G23_2", "G24_2")
RE_HEX = re.compile(r"^[a-f0-9]{64}$")
RE_SHA = re.compile(r"^[a-f0-9]{40}$")
MAX_BYTES = 32768
MAX_VALIDITY = timedelta(minutes=15)


def read_regular(path, max_bytes=MAX_BYTES):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size > max_bytes:
        raise RuntimeError("UNSAFE_OR_UNBOUNDED_GATE_FILE")
    return p.read_bytes()


def parse_utc(text):
    if not isinstance(text, str):
        raise RuntimeError("UTC_REQUIRED")
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError("INVALID_UTC") from exc
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise RuntimeError("UTC_REQUIRED")
    return value


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


class ExternalGateVerifier:
    def __init__(self, trust_dir, enforce_root_owned=True, clock=None):
        self.root = Path(trust_dir)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        if self.root.is_symlink() or not self.root.is_dir():
            raise RuntimeError("TRUST_DIRECTORY_UNAVAILABLE")
        if enforce_root_owned:
            for path in (self.root, *self.root.parents):
                if path == Path("/"):
                    continue
                info = path.lstat()
                if stat.S_ISLNK(info.st_mode) or info.st_mode & 0o022:
                    raise RuntimeError("TRUST_PATH_WRITABLE_OR_SYMLINK")
                if info.st_uid != 0:
                    raise RuntimeError("TRUST_PATH_NOT_ROOT_OWNED")
        self.trust_file = self.root / "trust.json"
        self._file_check(self.trust_file, enforce_root_owned)
        try:
            self.trust = json.loads(read_regular(self.trust_file))
        except (ValueError, UnicodeDecodeError) as exc:
            raise RuntimeError("TRUST_METADATA_INVALID") from exc
        if (self.trust.get("schema") != "LRB_TRUST_ROOTS/0.3"
                or set(self.trust.get("signers", {})) != set(ROLES)):
            raise RuntimeError("TRUST_ROOTS_NOT_COMPLETE")
        fingerprints = []
        issuer_ids = []
        self.public_keys = {}
        for role in ROLES:
            identity = self.trust["signers"][role]
            if (not isinstance(identity, dict) or not isinstance(identity.get("issuer_id"), str)
                    or not identity["issuer_id"] or not isinstance(identity.get("key_filename"), str)
                    or Path(identity["key_filename"]).name != identity["key_filename"]
                    or identity["key_filename"] in (".", "..")
                    or not isinstance(identity.get("sha256"), str)
                    or not RE_HEX.fullmatch(identity["sha256"])):
                raise RuntimeError("INVALID_TRUST_ROLE_" + role)
            pem = self.root / identity["key_filename"]
            self._file_check(pem, enforce_root_owned)
            raw = read_regular(pem)
            if sha256_bytes(raw) != identity["sha256"]:
                raise RuntimeError("PUBLIC_KEY_HASH_MISMATCH_" + role)
            fingerprints.append(identity["sha256"])
            issuer_ids.append(identity["issuer_id"])
            self.public_keys[role] = pem
        if len(set(fingerprints)) != len(ROLES) or len(set(issuer_ids)) != len(ROLES):
            raise RuntimeError("INDEPENDENT_ROLES_SHARE_A_KEY_OR_ISSUER")

    @staticmethod
    def _file_check(path, enforce):
        if Path(path).is_symlink() or not Path(path).is_file():
            raise RuntimeError("MISSING_OR_LINKED_TRUST_FILE")
        if enforce:
            info = Path(path).stat()
            if info.st_uid != 0 or info.st_mode & 0o022:
                raise RuntimeError("UNTRUSTED_PERMISSION_OR_OWNER")

    def sig(self, role, document, signature):
        # OpenSSL verifies detached SHA256/RSA signatures. Keys are provisioned
        # out-of-band and pinned; no private key or signature issuance here.
        read_regular(document)
        sigbytes = read_regular(signature, 8192)
        if len(sigbytes) < 64:
            raise RuntimeError("SIGNATURE_MISSING_OR_SHORT_" + role)
        try:
            proc = subprocess.run(
                ["openssl", "dgst", "-sha256", "-verify", str(self.public_keys[role]),
                 "-signature", str(signature), str(document)],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=5, check=False)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("OPENSSL_VERIFIER_UNAVAILABLE") from exc
        if proc.returncode != 0 or b"Verified OK" not in proc.stdout:
            raise RuntimeError("INVALID_SIGNATURE_" + role)

    def receipt(self, role, document, signature, request_hash, expected_host, expected_boot,
                source_sha, prior_hash=None):
        self.sig(role, document, signature)
        record = json.loads(read_regular(document))
        identity = self.trust["signers"][role]
        if (record.get("schema") != "LRB_SIGNED_GATE/0.3" or record.get("role") != role
                or record.get("issuer_id") != identity["issuer_id"] or record.get("decision") != "PASS"
                or record.get("request_sha256") != request_hash
                or record.get("host") != expected_host or record.get("boot_id") != expected_boot
                or record.get("source_sha256") != source_sha):
            raise RuntimeError("GATE_SCOPE_IDENTITY_OR_DECISION_MISMATCH_" + role)
        issued = parse_utc(record.get("issued_utc"))
        expires = parse_utc(record.get("expires_utc"))
        now = self.clock()
        if (issued > now + timedelta(seconds=30) or now >= expires
                or expires <= issued or expires - issued > MAX_VALIDITY):
            raise RuntimeError("GATE_STALE_OR_INVALID_TIME_" + role)
        if prior_hash and record.get("depends_on_sha256") != prior_hash:
            raise RuntimeError("INDEPENDENT_GATE_CHAIN_MISMATCH_" + role)
        return sha256_bytes(read_regular(document)), issued

    def preflight(self, request_path, owner_signature, receipts, strong=False,
                  expected_host=None, expected_boot=None):
        request_raw = read_regular(request_path)
        self.sig("OWNER", request_path, owner_signature)
        req = json.loads(request_raw)
        sha = sha256_bytes(request_raw)
        host = expected_host or os.uname().nodename
        boot = expected_boot or base.boot_id()
        if (req.get("schema") != "LRB_SCOPED_REQUEST/0.3"
                or not isinstance(req.get("mission_id"), str) or not req["mission_id"]
                or not isinstance(req.get("scope_id"), str) or not req["scope_id"]
                or req.get("host") != host or req.get("boot_id") != boot
                or not isinstance(req.get("source_sha256"), str)
                or not RE_HEX.fullmatch(req["source_sha256"])
                or req.get("capability") not in ("CAP_STORAGE_INSPECT", "CAP_SUDO_BASH",
                                                "CAP_BOOT_RECOVERY", "CAP_FSTAB_FIX")
                or req.get("risk") not in ("ROOT_READONLY", "ROOT_MUTATION", "BOOT")
                or not isinstance(req.get("owner_objective_sha256"), str)
                or not RE_HEX.fullmatch(req["owner_objective_sha256"])):
            raise RuntimeError("OWNER_REQUEST_SCOPE_INVALID")
        declared_risks = {"CAP_STORAGE_INSPECT": "ROOT_READONLY", "CAP_SUDO_BASH": "ROOT_MUTATION",
                          "CAP_BOOT_RECOVERY": "BOOT", "CAP_FSTAB_FIX": "ROOT_MUTATION"}
        if req["risk"] != declared_risks[req["capability"]]:
            raise RuntimeError("CAPABILITY_RISK_MISMATCH")
        now = self.clock()
        expiry = parse_utc(req.get("deadline_utc"))
        if expiry <= now or expiry - now > MAX_VALIDITY:
            raise RuntimeError("OWNER_REQUEST_DEADLINE_INVALID")
        required = ("G23", "G24", "G23_2", "G24_2") if strong else ("G23", "G24")
        if any(role not in receipts or set(receipts[role]) != {"document", "signature"}
               for role in required):
            raise RuntimeError("INDEPENDENT_RECEIPTS_MISSING")
        g23_hash, g23_issued = self.receipt("G23", receipts["G23"]["document"],
            receipts["G23"]["signature"], sha, host, boot, req["source_sha256"])
        g24_hash, g24_issued = self.receipt("G24", receipts["G24"]["document"],
            receipts["G24"]["signature"], sha, host, boot, req["source_sha256"], g23_hash)
        if g24_issued < g23_issued:
            raise RuntimeError("G24_PRECEDES_G23")
        hashes = {"request_sha256": sha, "g23_sha256": g23_hash, "g24_sha256": g24_hash}
        if strong:
            g23_2_hash, g23_2_issued = self.receipt("G23_2",
                receipts["G23_2"]["document"], receipts["G23_2"]["signature"],
                sha, host, boot, req["source_sha256"], g23_hash)
            g24_2_hash, g24_2_issued = self.receipt("G24_2",
                receipts["G24_2"]["document"], receipts["G24_2"]["signature"],
                sha, host, boot, req["source_sha256"], g24_hash)
            if g23_2_issued < g23_issued or g24_2_issued < max(g24_issued,g23_2_issued):
                raise RuntimeError("SECOND_ORDER_CHRONOLOGY_INVALID")
            if json.loads(read_regular(receipts["G24_2"]["document"])).get(
                    "depends_on_secondary_sha256") != g23_2_hash:
                raise RuntimeError("SECOND_ORDER_SECONDARY_CHAIN_MISMATCH")
            hashes.update({"g23_2_sha256":g23_2_hash, "g24_2_sha256":g24_2_hash})
        return {"schema": SCHEMA, "status": "SIGNED_RECEIPTS_CRYPTOGRAPHICALLY_VERIFIED",
                "scope_id": req["scope_id"], "capability": req["capability"],
                "host": host, "boot_id": boot, "hashes": hashes,
                "strong_second_order_receipts_verified": strong,
                "issuer_independence_externally_audited": False,
                "execution_authorized_by_this_verifier": False,
                "certified": False}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--trust-dir", default="/etc/louksna/remote-bridge")
    p.add_argument("--request", required=True)
    p.add_argument("--owner-signature", required=True)
    for role in ("g23", "g24", "g23-2", "g24-2"):
        p.add_argument("--" + role)
        p.add_argument("--" + role + "-signature")
    p.add_argument("--strong", action="store_true")
    p.add_argument("--state-dir", required=True)
    a = p.parse_args(argv)
    try:
        verifier = ExternalGateVerifier(a.trust_dir, enforce_root_owned=True)
        refs = {}
        for role in ("g23","g24","g23-2","g24-2"):
            d = getattr(a,role.replace("-","_"))
            s = getattr(a,role.replace("-","_")+"_signature")
            if d and s:
                refs[role.upper().replace("-","_")] = {"document":d,"signature":s}
        report = verifier.preflight(a.request,a.owner_signature,refs,strong=a.strong)
        base.EvidenceLedger(base.secure_state(a.state_dir)).append(
            "EXTERNAL_SIGNATURE_PREFLIGHT", report)
        print(json.dumps(report, indent=2,sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status":"HOLD","reason":str(exc)[:150],
                          "execution_authorized":False,"certified":False}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
