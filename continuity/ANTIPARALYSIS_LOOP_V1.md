# ANTIPARALYSIS LOOP V1

- ID: LOUKSNA-ANTIPARALYSIS-001
- Version: 1.0.0
- Status: IMPLEMENTED / BINDING ON BOTH RAILS
- Complements: DEFINITIVE_OPERATING_CONTRACT_V1.md

## Rule zero

Fail-closed stops unsafe advance.
Antiparalysis forbids permanent stillness without a registered next action.
If evidence is missing → search. If a solution is found → apply, verify, resume.

## Stages

### 1. MONITOR
Detect HOLD, failure, missing evidence, drift, or unmet gate.

### 2. REGISTER
Write a KEDB-compatible entry (`continuity/KEDB_SCHEMA_V1.json`):
- symptom, scope (SUPER1200 | DIRECTIVA | SHARED)
- evidence present / missing
- hashes, branch, SHA
- status: OPEN | KNOWN_ERROR | RESEARCHING | REMEDIATING | VERIFIED | RESUMED | HOLD_CONSCIOUS
- next_action (mandatory)

A log line alone is insufficient.

### 3. ANALYZE (+ metacognition)
Answer explicitly:
- Where are we?
- Why blocked?
- Is evidence present?
- Is there a known solution (`KNOWN_SOLUTIONS.md` or KEDB)?
- What is the single next action?

### 4. SEARCH (mandatory when evidence or solution is absent)
Investigation order (reuse existing SOL-002 hierarchy):
1. Branch evidence and canonical governance
2. Local solution registry / KEDB
3. Academic / paper evidence
4. Senior / SRE practice
5. GitHub (issues, workflows, trusted repos)
6. Hugging Face (evaluation / skill papers) when relevant

External sources never grant certification by themselves.
Search outcomes must be written back into the registry.

### 5. PLAN
Bounded remediation only:
- exact files/scope
- verification command/condition
- rollback reference
- provenance fields

Forbidden: authority changes, secret changes, silent scope expansion, infinite retries with identical hashes.

### 6. EXECUTE (apply)
Apply the patch or operational step.
Do not leave solutions as documentation-only when application is safe and in scope.

### 7. VERIFY
Re-run the failing condition with independent checks where required.
Results: PASS | FAIL | UNABLE_TO_DETERMINE.
UNABLE_TO_DETERMINE is not PASS.

### 8. RESUME
Load checkpoint + applied solution state.
Continue from last completed unit; do not redo verified work.

### 9. KNOWLEDGE + TELEMETRY
Update KEDB entry and emit telemetry (`TELEMETRY_SCHEMA_V1.json`).

## Admission gates (non-compensatory)

Missing evidence cannot be offset by high confidence, green unrelated CI, or narrative.
Silent success (checks not run treated as pass) is forbidden.

## Boundedness

- Max automatic remediation attempts per identical hash set: 3
- Then HOLD_CONSCIOUS with explicit human or research next_action
- No recursive self-executor registration
