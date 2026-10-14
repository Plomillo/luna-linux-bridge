# ANTIPARALYSIS LOOP V1

- ID: LOUKSNA-ANTIPARALYSIS-001
- Version: 1.0.0
- Status: IMPLEMENTED / BINDING ON BOTH RAILS

## Rule zero

Fail-closed stops unsafe advance.
Antiparalysis forbids permanent stillness without a registered next action.
If evidence is missing → search. If a solution is found → apply, verify, resume.

## Stages

MONITOR → REGISTER → ANALYZE(+metacognition) → SEARCH(if needed) → PLAN → EXECUTE(apply) → VERIFY → RESUME → KNOWLEDGE+TELEMETRY

## Admission

Missing evidence cannot be compensated. UNABLE_TO_DETERMINE is not PASS.
Bounded remediation: max 3 attempts per identical hash set, then HOLD_CONSCIOUS.
