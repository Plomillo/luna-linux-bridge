# MISSION ERROR / HOLD

MISSION_ID = UNDECLARED
MAIL_ID = MAIL-8CC285625346E4675D8B
MISSION_STATUS = HOLD

ERROR_ID = MAIL-8CC285625346E4675D8B-EXECUTOR_BINDING
ERROR_STATE = TRUE

EXPECTED_STATE = EXECUTOR_BINDING=PASS
OBSERVED_STATE = executor_reported=UNBOUND_MEDIATED_OR_LOCAL

ROOT_CAUSE = CUSTOSZ_EXECUTOR_UNBOUND
ROOT_CAUSE_CONFIDENCE = C3_VERIFIED

EVIDENCE = ROUTING_DECISION.json + RUNTIME_COMPATIBILITY.json
SOURCE = CUSTOSZ_MISSION_MAILBOX
RUN_ID = 36389867885
SOURCE_COMMIT = 1b2b1eb329a7e75277eaf0de073e995fb431cebe
SOURCE_HASH = 8cc285625346e4675d8b6fba4b4545ee42b0255057d8109db3e48a1e061558b9

AFFECTED_GATE = EXECUTOR_BINDING

EXACT_REMEDIATION = Bind a governed executor in CUSTOSZ/Runtime for this mission class; do not substitute Desktop or an implicit shell.

REMEDIATION_PRECONDITIONS = preserve original mission hash and Louksna authority
REMEDIATION_SCOPE = mailbox / CUSTOSZ routing / Runtime adapter layer only unless separately authorized
FORBIDDEN_SIDE_EFFECTS = no canonical mutation; no silent executor substitution; protected scopes remain denied

VERIFICATION_TEST = rerun the same native envelope and require EXECUTOR_BINDING=PASS
EXPECTED_VERIFICATION_RESULT = PASS

ROLLBACK = revert only the corrective mailbox/adapter change
ROLLBACK_VERIFICATION = original mission SHA-256 remains unchanged

NEXT_ROUTE = CUSTOSZ_ROUTER
NEXT_ACTION = apply exact remediation and rerun compatibility

RESOLVED = FALSE
