# DEFINITIVE OPERATING CONTRACT V1

- ID: LOUKSNA-DEFINITIVE-OPERATING-001
- Version: 1.0.0
- Status: IMPLEMENTED / NOT GLOBALLY CERTIFIED
- Authority: Louksna.md + this contract
- Applies to: SUPER1200 (custosz/super-1200-implementation-20261007) and Directiva/mTLS (automation/mtls-evidence-gate-20261013)
- Policy: EXTEND_DO_NOT_REPLACE · APPEND_ONLY · FAIL_CLOSED · NO_SILENT_OPERATIONS · NO_DECORATIVE_WORK
- Prohibition: do not merge or promote to `main` without explicit authorization and real G23 then G24.

## 1. Purpose

Keep both rails alive with continuous automation, without lowering controls.
If evidence is missing, search for it. If a solution exists, apply it, verify it, and resume from checkpoint — never from zero, never as a note-only outcome.

## 2. Always-on principles

1. **Fail-closed** — no admissible evidence → no advance; never silent PASS.
2. **Antiparalysis** — every HOLD/failure produces a registry entry + mandatory next action.
3. **Evidence search** — if evidence is absent, investigation is required work, not optional.
4. **Apply solutions** — known or researched fixes are applied, verified, and recorded.
5. **Resume** — checkpoint + applied patch; do not restart completed work.
6. **Metacognition** — system state must answer: where we are, why blocked, what is next.
7. **Telemetry** — actionable fields only (see TELEMETRY_SCHEMA_V1.json).
8. **Provenance** — SHA, hashes, actor, UTC timestamp on every consequential artifact.
9. **Governance chain** — SOURCE → INPUT → OPERATION → OUTPUT → TEST → VALIDATION → INDEPENDENT_VALIDATION → CERTIFICATION.
10. **Nothing decorative** — activity without state change or evidence is forbidden.

## 3. Shared loop (MAPE-K + KEDB + Proof-or-Stop)

```
MONITOR → REGISTER → ANALYZE(+metacognition)
  → if no evidence: SEARCH
  → if solution known/found: PLAN → EXECUTE(apply) → VERIFY
  → RESUME from checkpoint
  → KNOWLEDGE + TELEMETRY
```

Details: `continuity/ANTIPARALYSIS_LOOP_V1.md`
Registry schema: `continuity/KEDB_SCHEMA_V1.json`
Telemetry schema: `continuity/TELEMETRY_SCHEMA_V1.json`

## 4. Rail A — SUPER1200 (1200 capabilities / D01–D22)

- Current material checkpoint: D05_129_132_MATERIALIZED (scoped G23/G24 only).
- Global certification: NOT_CERTIFIED.
- Prepare continuation rail for D06–D22: `implementation/super1200/DOMAIN_RAIL_D06_D22.md`.
- Advance only by reviewed material executors + behavioural tests + scoped gates.
- Existing contract remains in force: `SUPER1200_CONTINUOUS_AUTOMATION_CONTRACT.md` (extended, not replaced).

## 5. Rail B — Directiva (GitHub-only unlock)

- Goal: trustworthy remote (Louksna Zona Directiva) for final client use on Debian.
- Non-negotiable: do not use the owner's HP notebook as primary host; do not use third-party machines.
- Unlock requires host evidence + separated G23/G24 identities consumable by GitHub Actions.
- Contract: `continuity/DIRECTIVA_GITHUB_ONLY_UNLOCK_V1.md`.

## 6. Freeze / resume

During implementation of this contract, both rails may be marked PAUSED_FOR_CONTRACT_WIRING.
Resume only when:
1. This contract and the antiparalysis loop files exist on the candidate branch(es).
2. KEDB + telemetry schemas are present.
3. Domain rail D06–D22 marker exists.
4. Directiva unlock contract exists.
5. Freeze marker `continuity/IMPLEMENTATION_FREEZE_RESUME_V1.json` sets `resume_authorized: true`.

## 7. Hardening as colleague

Hardening blocks lies and forces search → apply → verify → resume.
It is not an enemy of progress; it is the condition of real progress.

## 8. Certification

This contract is implemented as governance artifacts.
It is NOT a global SUPER1200 or Directiva G24 certificate.
