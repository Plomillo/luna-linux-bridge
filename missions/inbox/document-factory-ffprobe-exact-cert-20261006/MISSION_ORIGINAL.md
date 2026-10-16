MISSION_ID = MIS-DOCUMENT-FACTORY-FFPROBE-EXACT-CERT-20261006
MISSION_CLASS = DOCUMENT_FACTORY_GOVERNED_CONTINUATION_V1
AUTHORITY = Louksna.md
WORKER = CUSTOSZ_V7
RUNTIME = CUSTOSZ_RUNTIME_V1
EXECUTION_LOCATION = SELF_HOSTED_LUNA_AUX
FAILURE_POSTURE = FAIL_CLOSED
NO_SILENT_OPERATIONS = TRUE
REMOTE_DESKTOP_COMMANDER = PROHIBITED
DESKTOP_EXECUTION = PROHIBITED
CERTIFICATION_PROPAGATION = FORBIDDEN
AUTO_MERGE = FORBIDDEN
OPERATIONAL_ACTIVATION = FORBIDDEN
TARGET_TERMINAL_STATE = CERTIFIED_NOT_ACTIVE
WALLCLOCK_CEILING_SECONDS = 1200

OBJECTIVE
Close the exact Document Factory FFprobe candidate certification chain without changing canonical authority or inheriting certification from another object.

MATERIAL ANCHORS
WORK_SHA = 3cc413cea40d77c7bb119e29d09d72b4eac44909
LEGACY_CANDIDATE_SHA = 3774cb102ad6318fc824b2cb87c5055e9f5f4b0b

MANDATORY ORDER
1. IDENTITY_GATE
   Compare WORK_SHA and LEGACY_CANDIDATE_SHA materially and cryptographically. Commit-message equality is not evidence of material equality. Record commit/tree/file/digest evidence.
   If exact admissible equivalence is not demonstrated, derive/promote EXACT_CANDIDATE_SHA from WORK_SHA.
   Freeze EXACT_CANDIDATE_SHA and its artifact SHA-256.

2. FRESH_PRODUCER
   Run only against EXACT_CANDIDATE_SHA. Preserve provenance, dependency pins, run ID, logs and artifact digest. Any mismatch => ABORT.

3. INDEPENDENT_PRODUCER
   Run independently against the same EXACT_CANDIDATE_SHA. Preserve independence evidence and immutable output digest. Any identity drift => ABORT.

4. G23_INDEPENDENT_VALIDATION
   Validate exactly the independently produced SHA/digest. Require complete evidence chain and non-regression. G23 may not validate a different object.

5. G24_CERTIFICATION
   Execute only after G23=PASS and on exactly the same SHA/digest. No inheritance and no propagation.

6. TERMINAL_RECORD
   Only after G24=PASS record CERTIFIED_NOT_ACTIVE.
   Do not merge to main. Do not operationally activate. Do not mutate Louksna.md, PUAC2, frozen authority, or prior ACTIVE certification.
   Preserve checkpoint, rollback and immutable evidence pointers.

REQUIRED LIVE TELEMETRY
IDENTITY_GATE={RUNNING|PASS|FAIL}
EXACT_CANDIDATE_SHA=<sha>
EXACT_CANDIDATE_DIGEST=<sha256>
FRESH_PRODUCER={RUNNING|PASS|FAIL};RUN_ID=<id>
INDEPENDENT_PRODUCER={RUNNING|PASS|FAIL};RUN_ID=<id>
G23={RUNNING|PASS|FAIL};RUN_ID=<id>
G24={RUNNING|PASS|FAIL};RUN_ID=<id>
TERMINAL_STATE={CERTIFIED_NOT_ACTIVE|ABORTED}
EVIDENCE_POINTERS=<immutable refs>

COORDINATION
CUSTOSZ V7 is the worker. CUSTOSZ_RUNTIME_V1 is the governed execution control. GitHub/LOUKSNA Remote Bridge is transport, ingress, routing, telemetry and evidence. Desktop and Remote Desktop Commander are forbidden as worker, fallback, auxiliary executor, evidence transporter or recovery path.

STOP/RETURN RULE
Once CUSTOSZ V7 + Runtime emit live telemetry proving this exact chain is RUNNING, continue autonomously. Do not request conversational intervention unless a fail-closed gate requires new explicit authorization.
