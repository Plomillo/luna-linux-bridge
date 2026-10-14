# DIRECTIVA — GitHub-only unlock contract V1

- ID: DIRECTIVA-GITHUB-ONLY-UNLOCK-001
- Version: 1.0.0
- Status: BINDING
- Branch context: automation/mtls-evidence-gate-20261013 (and related Louksna ZD work)
- Parent: DEFINITIVE_OPERATING_CONTRACT_V1

## Non-negotiable constraints

1. Do **not** use the owner's HP notebook (8GB RAM) as primary host for continuous privileged work.
2. Do **not** use third-party / foreign computers.
3. Unlock and certification evidence must be consumable by **GitHub Actions** (self-hosted runner labels or equivalent GitHub-orchestrated evidence path).

## What unlock means

Unlock is not more feature code. Unlock is admissible evidence:

### Host evidence
- Self-hosted runner online with required labels (e.g. self-hosted, linux, x64, luna-aux) **or** a documented GitHub-native equivalent path that produces the same verifiable host reports
- Real mTLS config and service state as required by PUAC-2 / readiness probe
- Host test report + rollback report variables/artifacts bound to candidate SHA

### Identity evidence
- Separated G23 and G24 signing keys and public materials
- Distinct validator/certifier IDs

### Gate behaviour
- Readiness probe remains continuous and fail-closed
- Missing evidence → HOLD + KEDB entry + next_action
- If evidence is missing → **search** for GitHub-only mechanisms (documented in KEDB research_summary)
- When evidence appears → apply path already wired (dispatch/schedule) → verify → G23 then G24

## Antiparalysis on this rail

Stillness without registry entry is forbidden.
HOLD is allowed; silent permanent freeze is not.

## Non-claims

- This contract does not assert that host evidence currently exists.
- This contract does not certify the remote for final-client use until G23/G24 pass on real evidence.
