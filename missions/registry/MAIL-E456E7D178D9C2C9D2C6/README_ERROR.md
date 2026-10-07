# MISSION ERROR / HOLD

MISSION_ID = MAILBOX-SELFTEST-001
MAIL_ID = MAIL-E456E7D178D9C2C9D2C6
MISSION_STATUS = HOLD

ERROR_ID = MAIL-E456E7D178D9C2C9D2C6-EXECUTOR_BINDING
ERROR_STATE = TRUE

EXPECTED_STATE = EXECUTOR_BINDING=PASS
OBSERVED_STATE = executor_reported=UNBOUND_MEDIATED_OR_LOCAL

ROOT_CAUSE = CUSTOSZ_EXECUTOR_UNBOUND
ROOT_CAUSE_CONFIDENCE = C3_VERIFIED

EVIDENCE = ROUTING_DECISION.json + RUNTIME_COMPATIBILITY.json
SOURCE = CUSTOSZ_MISSION_MAILBOX
RUN_ID = 36389383039
SOURCE_COMMIT = ba3978770ed2d2814882c239f2625c26b993023d
SOURCE_HASH = e456e7d178d9c2c9d2c630434cea45ec2513084750c9d9bcadac14d970ed448e

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
