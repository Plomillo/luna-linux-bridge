# MISSION ERROR / HOLD

MISSION_ID = MIS-DOCUMENT-FACTORY-FFPROBE-EXACT-CERT-V2-20261006
MAIL_ID = MAIL-79820A3F665F55ACF54A
MISSION_STATUS = HOLD

ERROR_ID = MAIL-79820A3F665F55ACF54A-RUNTIME_ADAPTER
ERROR_STATE = TRUE

EXPECTED_STATE = RUNTIME_ADAPTER=PASS
OBSERVED_STATE = executor_bound=False; matching_adapters=0; rejected_adapters=9

ROOT_CAUSE = NO_UNIQUE_PINNED_RUNTIME_ADAPTER
ROOT_CAUSE_CONFIDENCE = C3_VERIFIED

EVIDENCE = ROUTING_DECISION.json + RUNTIME_COMPATIBILITY.json
SOURCE = CUSTOSZ_MISSION_MAILBOX
RUN_ID = 37496487426
SOURCE_COMMIT = 576e770d6e96bc824d71ddb5d619e7b5f8b65f86
SOURCE_HASH = 79820a3f665f55acf54a444257305257c2b6a039d2111b31d5ee7743701b5e6b

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
