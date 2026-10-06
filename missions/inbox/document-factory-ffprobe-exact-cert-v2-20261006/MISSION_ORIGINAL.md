MISSION_ID = MIS-DOCUMENT-FACTORY-FFPROBE-EXACT-CERT-V2-20261006
MISSION_CLASS = DOCUMENT_FACTORY_FFPROBE_EXACT_CERT_V1
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
MATERIAL_CANDIDATE_SHA = 3774cb102ad6318fc824b2cb87c5055e9f5f4b0b
FRESH_PRODUCER_EVIDENCE_SHA = 3cc413cea40d77c7bb119e29d09d72b4eac44909
IDENTITY_RELATION = DIVERGED_FROM_COMMON_ACTIVE_ANCHOR_WITH_FRESH_PRODUCER_EVIDENCE_ADDITION

MANDATORY ORDER
1. IDENTITY_GATE: verify the material candidate and fresh-producer evidence relationship cryptographically; no commit-message equivalence.
2. FRESH_PRODUCER: validate evidence for the exact material candidate and freeze immutable artifact digest.
3. INDEPENDENT_PRODUCER: independently produce/validate the same exact material candidate and preserve immutable output digest.
4. G23_INDEPENDENT_VALIDATION: validate exactly the independently produced SHA/digest with complete evidence and non-regression.
5. G24_CERTIFICATION: execute only after G23=PASS on exactly the same SHA/digest; no inheritance or propagation.
6. TERMINAL_RECORD: only after G24=PASS record CERTIFIED_NOT_ACTIVE. No main merge and no operational activation.

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
CUSTOSZ V7 is the worker. CUSTOSZ_RUNTIME_V1 is the governed execution control. GitHub/LOUKSNA Remote Bridge is transport, ingress, routing, telemetry and evidence. Desktop and Remote Desktop Commander are forbidden.

STOP/RETURN RULE
Once CUSTOSZ V7 + Runtime emit live telemetry proving this exact chain is RUNNING, continue autonomously. Do not request conversational intervention unless a fail-closed gate requires new explicit authorization.
