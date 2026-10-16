# DIRECTIVA — Definitive host provisioning unstick V1

- ID: DIRECTIVA-HOST-PROVISION-UNSTICK-001
- Status: ACTIONABLE
- Branch: automation/mtls-evidence-gate-20261013
- Observed: workflow_dispatch run 38492775989 reached the self-hosted runner (luna-aux) and failed only on missing host config.

## Exact blocker (from logs)

Job `Real host mTLS and rollback evidence` failed with:

```
Missing, non-regular, or symlinked trusted host config: /etc/louksna/remote-bridge/mtls.json
```

The runner itself is present and accepted the job. The missing piece is the host configuration and service evidence.

## Required on the runner (root, non-world-writable)

1. Create `/etc/louksna/remote-bridge/mtls.json`
   - Regular file (not symlink)
   - Owned by root (uid 0)
   - Mode not group/world writable (e.g. 0640 or stricter)

2. Ensure `louksna-remote-bridge.service` is active (`systemctl is-active`)

3. Place client cert, key, and CA where the workflow variables point:
   - `PUAC2_MTLS_CLIENT_CERT`
   - `PUAC2_MTLS_CLIENT_KEY`
   - `PUAC2_MTLS_CA_CERT`

4. Produce and point to:
   - `PUAC2_HOST_TEST_REPORT` (schema PUAC2_HOST_TEST_REPORT/1.0, status PASS, bound to candidate SHA)
   - `PUAC2_ROLLBACK_TEST_REPORT` (schema PUAC2_ROLLBACK_REPORT/1.0, status PASS, rollback_verified true)

5. Configure separated G23/G24 identities (secrets + vars) as already listed in the readiness probe.

## Non-negotiable

- Do not use the owner HP notebook as primary host.
- Do not use third-party machines.
- Evidence must be consumable by GitHub Actions (this runner or equivalent).

## Next action

Provision the above on the existing luna-aux runner, then re-dispatch `puac2-autonomous.yml` on this branch. The readiness probe and gates are already wired; they will advance when the evidence appears.

No silent PASS. HOLD remains until the files exist.
