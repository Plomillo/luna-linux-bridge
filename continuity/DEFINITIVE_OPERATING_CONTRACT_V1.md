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

## 3. Shared loop

See ANTIPARALYSIS_LOOP_V1.md, KEDB_SCHEMA_V1.json, TELEMETRY_SCHEMA_V1.json.

## 4. This rail — Directiva

See DIRECTIVA_GITHUB_ONLY_UNLOCK_V1.md.
Readiness remains fail-closed. Missing host evidence → KEDB + search.

## 5. Certification

Governance artifacts only. NOT a G24 certificate for the remote.
