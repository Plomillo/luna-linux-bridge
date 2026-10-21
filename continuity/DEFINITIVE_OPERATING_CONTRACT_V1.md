# DEFINITIVE OPERATING CONTRACT V1

- ID: LOUKSNA-DEFINITIVE-OPERATING-001
- Version: 1.0.0
- Status: IMPLEMENTED / CERTIFIED_SCOPE_93_1200 / NOT WHOLE CATALOG
- Authority: Louksna.md + this contract
- Applies to: SUPER1200 (custosz/super-1200-implementation-20261007) and Directiva/mTLS (automation/mtls-evidence-gate-20261013)
- Policy: EXTEND_DO_NOT_REPLACE · APPEND_ONLY · FAIL_CLOSED · NO_SILENT_OPERATIONS · NO_DECORATIVE_WORK
- Prohibition: this promotion to `main` is only the sealed rail after explicit authorization and real G23 then G24. It is not a whole-catalog certificate. Capabilities 1–92 stay withheld. Synthetic materializer stays disabled. Any wider scope still requires a new G23 then G24.

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

- Current seal: `GLOBAL_CERTIFIED_SCOPE_93_1200` (1108 capabilities). Certificate: `continuity/certification/SUPER1200_GLOBAL.json`.
- Withheld: capabilities 1–92. They have no scoped certificate on this SHA. Do not infer them from the seal.
- Whole-catalog claim: false. A scoped PASS does not propagate to another capability or to the catalog.
- Synthetic materializer: DISABLED.
- Promotion of this rail to `main` is the git merge after G23 then G24. The seal field `promotion_to_main` stays false so the certificate itself is not a blank check.
- D04:93–96 and D04:97–100 are rebound to the current `D04_runtime.py` / `test_d04_runtime.py` hashes. Prior module hashes and prior workflow ids are preserved.
- Advance into 1–92, or beyond 1200, only by reviewed material, behavioural tests, and a new scoped gate.
- Existing contract remains in force: `SUPER1200_CONTINUOUS_AUTOMATION_CONTRACT.md` (extended, not replaced).

## 5. Rail B — Directiva (GitHub-only unlock)

- Goal: trustworthy remote (Louksna Zona Directiva) for final client use on Debian.
- Non-negotiable: do not use the owner's HP notebook as primary host; do not use third-party machines.
- Unlock requires host evidence + separated G23/G24 identities consumable by GitHub Actions.
- Current checkpoint on this rail: `CONNECTIVITY_PROBE_DISPATCHED` (host bootstrap and connectivity probe). That status is not a certification.
- Contract: `continuity/DIRECTIVA_GITHUB_ONLY_UNLOCK_V1.md`.

## 6. Freeze / resume

Resume is authorized for the wired rails. It is not authorization to invent evidence.
Resume stays valid only while:
1. This contract and the antiparalysis loop files exist on the promoted branch.
2. KEDB + telemetry schemas are present.
3. The SUPER1200 seal, if claimed, matches `SUPER1200:93-1200` with withheld `[1, 92]`.
4. Directiva unlock contract exists and does not claim final-client certification.
5. Freeze marker `continuity/IMPLEMENTATION_FREEZE_RESUME_V1.json` sets `resume_authorized: true`.

## 7. Hardening as colleague

Hardening blocks lies and forces search → apply → verify → resume.
It is not an enemy of progress; it is the condition of real progress.

## 8. Certification

This contract is governance. It is not itself the G24 seal.
The SUPER1200 seal covers 93–1200 only, after independent G23 and a second G24 revalidation.
Directiva is not certified for final-client use until its own G23 then G24 pass on real host evidence.
Capabilities 1–92 are not certified.
