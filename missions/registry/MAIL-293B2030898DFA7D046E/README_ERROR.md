# MISSION ERROR / HOLD

MISSION_ID = MAIN_RECOVERY_SKELETON_CONSULTA_20261002
MAIL_ID = MAIL-293B2030898DFA7D046E
MISSION_STATUS = HOLD

ERROR_ID = MAIL-293B2030898DFA7D046E-RUNTIME_ADAPTER
ERROR_STATE = TRUE

EXPECTED_STATE = RUNTIME_ADAPTER=PASS
OBSERVED_STATE = executor_bound=False; matching_adapters=0; rejected_adapters=8

ROOT_CAUSE = NO_UNIQUE_PINNED_RUNTIME_ADAPTER
ROOT_CAUSE_CONFIDENCE = C3_VERIFIED

EVIDENCE = ROUTING_DECISION.json + RUNTIME_COMPATIBILITY.json
SOURCE = CUSTOSZ_MISSION_MAILBOX
RUN_ID = 37070241770
SOURCE_COMMIT = af7d55bba95e4b6dfeb1a816249badf902e2c676
SOURCE_HASH = 293b2030898dfa7d046e153f7ddf002297c22b04fce5ba1a98ee8f9f3fe7f87a

AFFECTED_GATE = RUNTIME_ADAPTER

EXACT_REMEDIATION = Register exactly one reviewed SHA-256-pinned adapter for this source SHA-256, mission class, scope and execution location. If the executor is initially unbound, the adapter must explicitly declare provides_executor_binding=true.

REMEDIATION_PRECONDITIONS = preserve original mission hash and Louksna authority
REMEDIATION_SCOPE = mailbox / CUSTOSZ routing / Runtime adapter layer only unless separately authorized
FORBIDDEN_SIDE_EFFECTS = no canonical mutation; no silent executor substitution; protected scopes remain denied

VERIFICATION_TEST = rerun the same native envelope and require RUNTIME_ADAPTER=PASS
EXPECTED_VERIFICATION_RESULT = PASS

ROLLBACK = revert only the corrective mailbox/adapter change
ROLLBACK_VERIFICATION = original mission SHA-256 remains unchanged

NEXT_ROUTE = CUSTOSZ_ROUTER
NEXT_ACTION = apply exact remediation and rerun compatibility

RESOLVED = FALSE
