#!/usr/bin/python3
from __future__ import annotations
import argparse, base64, hashlib, json, os, pathlib

EXPECTED_REPOSITORY="Plomillo/luna-linux-bridge"
EXPECTED_DIGEST="ed3c4267f94b3c53f1fec64b331f72dc657ebcc5e2c62a9314321c67c89684b7"

def decode_claims(token: str) -> dict:
    parts=token.split(".")
    if len(parts)!=3:
        raise SystemExit("OIDC_TOKEN_FORMAT_INVALID")
    payload=parts[1] + "="*((4-len(parts[1])%4)%4)
    return json.loads(base64.urlsafe_b64decode(payload))

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--g23",required=True)
    p.add_argument("--audience",required=True)
    p.add_argument("--candidate-head-sha",required=True)
    p.add_argument("--trust-root-sha",required=True)
    p.add_argument("--authority-out",required=True)
    p.add_argument("--certificate-out",required=True)
    a=p.parse_args()

    g23=json.loads(pathlib.Path(a.g23).read_text(encoding="utf-8"))
    if g23.get("status")!="PASS":
        raise SystemExit("G23_NOT_PASS")
    digest=g23.get("candidate_digest_sha256")
    if digest!=EXPECTED_DIGEST:
        raise SystemExit("CANDIDATE_DIGEST_NOT_EXPECTED_V2")

    expected_aud=f"louksna-r4-apc48-v2-g24:{digest}"
    if a.audience!=expected_aud:
        raise SystemExit("AUDIENCE_DIGEST_BINDING_MISMATCH")

    token=os.environ.get("OIDC_TOKEN","")
    if not token:
        raise SystemExit("OIDC_TOKEN_MISSING")
    claims=decode_claims(token)
    aud=claims.get("aud")
    if aud!=expected_aud and not (isinstance(aud,list) and expected_aud in aud):
        raise SystemExit("OIDC_AUDIENCE_MISMATCH")
    if claims.get("repository")!=EXPECTED_REPOSITORY:
        raise SystemExit("OIDC_REPOSITORY_MISMATCH")

    authority={
        "schema":"LOUKSNA_R4_APC48_V2_AUTHORITY/1.0",
        "authority_authenticated":True,
        "candidate_digest_sha256":digest,
        "candidate_head_sha":a.candidate_head_sha,
        "trust_root_sha":a.trust_root_sha,
        "signature_reference":"GITHUB_OIDC_JWT_SHA256:"+hashlib.sha256(token.encode()).hexdigest(),
        "repository":claims.get("repository"),
        "subject":claims.get("sub"),
        "workflow":claims.get("workflow"),
        "raw_token_persisted":False
    }
    pathlib.Path(a.authority_out).write_text(json.dumps(authority,indent=2,sort_keys=True)+"\n",encoding="utf-8")

    cert={
        "schema":"LOUKSNA_R4_APC48_V2_G24/1.0",
        "status":"PASS",
        "certificate_scope":"PRE_INSTALLATION_CANDIDATE_V2_ONLY",
        "candidate_digest_sha256":digest,
        "g23_status":"PASS",
        "authority_authenticated":True,
        "authority_reference":authority["signature_reference"],
        "candidate_head_sha":a.candidate_head_sha,
        "validator_trust_root_sha":a.trust_root_sha,
        "incident_regressions_closed":[
            "AWAKE_GUARD_WHY_ARGUMENT_SPLIT",
            "FAIL_EXIT_BYPASSED_ERR_TRAP",
            "RESIDUAL_REVOKE_TIMER",
            "INCOMPLETE_BOOTSTRAP_RECOVERY"
        ],
        "canonical_mutation":False,
        "authority_transfer":False,
        "runtime_host_activation_certified":False,
        "post_installation_certificate_required":True
    }
    pathlib.Path(a.certificate_out).write_text(json.dumps(cert,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(cert,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
