# Lunita v1.8 — Kestra evidence orchestration

**Status:** candidate integration; not a Lunita certificate.  
**Kestra:** Open Source v2.0.3, pinned patch tag.  
**Branch:** recovery/lunita-custoszv9-operational-20261020.

## Purpose

Kestra coordinates the evidence gates for the additive Lunita v1.8 candidate. It reads the latest recovery-contract CI run and its overlay artifact. When a target-runtime publication is present, it checks the exact receipt schema, candidate identity, CUSTOSZ_V7 worker binding, E01/Qwen, E04/INT8, E02–E15 test coverage including E15 consensus, and the preserved Brújula/R/Jamovi/JASP smoke results.

This flow is deliberately read-only. It does not run a shell, script, process, local model, Flatpak application, target command, or CUSTOSZ worker. It cannot issue G23, G24, S32, or a stable-release certificate. A Kestra execution ending in SUCCESS can contain a logged HOLD; it must never be interpreted as product certification.

## Runtime setup

The local Compose stack uses the reviewed Kestra v2.0.3 image and PostgreSQL 18.6-alpine. Both the UI and management ports bind to loopback. The one-shot storage bootstrap has no network and only the CHOWN capability. The long-running Kestra service is not configured as root. No Docker socket is mounted. Kestra HTTP tasks are restricted to api.github.com.

~~~bash
cd integrations/kestra
cp .env.example .env
chmod 600 .env
# Replace both password values with independent random secrets.
docker compose config --quiet
docker compose pull
docker compose up -d --wait --wait-timeout 300
~~~

Import flows/30-lunita-v1-8-certification-gate.yml in the Kestra UI at http://127.0.0.1:8080, namespace louksna.lunita, then execute lunita_v1_8_certification_gate manually. Do not expose the UI or management port publicly. No GitHub token is required because the flow reads only the public repository API.

## Target evidence publication contract

The target runtime receipt must first be produced by the already-authorized CUSTOSZ_V7 worker using TARGET_RUNTIME_V1_8_CUSTOSZ_V7_HANDOFF.md. GitHub-hosted CI and Kestra are not substitutes for that target execution.

Preserve the original timestamped receipt at an immutable path under:

evidence/lunita/target-runtime-acceptance/

Publish the current projection at:

evidence/lunita/target-runtime-acceptance/CURRENT.json

The projection schema is LUNITA_TARGET_RUNTIME_ACCEPTANCE_PUBLICATION/1.0 and contains:

~~~json
{
  "schema": "LUNITA_TARGET_RUNTIME_ACCEPTANCE_PUBLICATION/1.0",
  "candidate_id": "G06_REBUILD_CANDIDATE_R1",
  "source_receipt_path": "evidence/lunita/target-runtime-acceptance/LUNITA_TARGET_RUNTIME_ACCEPTANCE_<UTC_TIMESTAMP>.json",
  "source_receipt_sha256": "<SHA-256 of exact original receipt bytes>",
  "receipt": {
    "schema": "LUNITA_TARGET_RUNTIME_ACCEPTANCE/1.0",
    "status": "PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED",
    "worker_required": "CUSTOSZ_V7",
    "worker_version": "CUSTOSZ_V7",
    "certification": "NOT_GRANTED"
  }
}
~~~

The receipt property must contain the complete JSON body of the original CUSTOSZ_V7 receipt, not a summary or reconstructed result. source_receipt_sha256 must be calculated from the exact original bytes before publication. Keep every timestamped receipt; update only the current projection pointer. A blocked receipt remains evidence of a blocked run and must not be relabelled as a pass.

## Gate semantics

- Missing or unsuccessful current CI, or missing/expired overlay artifact: HOLD.
- Missing target publication: HOLD_CUSTOSZ_V7_RECEIPT_NOT_PUBLISHED.
- A blocked, stale, malformed, skipped, wrong-worker or wrong-candidate target receipt: HOLD.
- A valid target acceptance receipt: PASS_NOT_CERTIFIED, ready for the separate independent-validation lane. This is not G23 or G24.
- G23 remains with the independent validator. S32 and G24 remain separate issuance authorities. Kestra never grants them.

The published receipt projection is a read-only input to Kestra. The independent certification lane remains responsible for re-hashing its local original receipt, validating the complete rootfs/dependency inventory and all four JASP regression cases, and requiring its hash-bound S32 result before emitting LUNITA_STABLE_1_8.

## Static checks

~~~bash
python3 validate.py
~~~

The lunita-kestra-gate.yml GitHub Actions workflow starts an ephemeral Kestra/PostgreSQL instance, imports and executes this flow, records execution evidence, and destroys the temporary stack. It proves Kestra can parse and run the coordinator; it does not install a persistent Kestra service on the target machine and does not certify the target runtime.
