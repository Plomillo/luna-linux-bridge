# CUSTOSZ Mission Mailbox

STATUS = STAGED_PENDING_VALIDATION
VERSION = 0.1.0
AUTHORITY = Louksna.md
WORKER = CUSTOSZ_V7
GOVERNOR = MetaOS
SUPERVISOR = SYMPHYLAX_R1
RUNTIME = CUSTOSZ_RUNTIME_V1
EVOLUTION_REVIEW = CUSTOSZ_FAMILY_9

## Purpose

Mission Mailbox is a governed ingress, normalization, routing and evidence bridge between GitHub and CUSTOSZ.

GitHub is transport, registry, evidence and provenance. GitHub is not the worker, governor or canonical authority.

MISSION_ORIGINAL
-> GITHUB_MAILBOX
-> INGRESS_VALIDATION
-> BYTE_EXACT_NATIVE_ENVELOPE
-> CUSTOSZ_ROUTER
-> RUNTIME_COMPATIBILITY
-> EXECUTOR_BINDING
-> MATERIAL_EXECUTION
-> VALIDATION / ROLLBACK / EVIDENCE
-> TERMINAL_REPORT
-> FAMILY_9_CAPABILITY_SUGGESTIONS

## Authority separation

- Louksna.md = canonical authority.
- MetaOS = governor.
- CUSTOSZ V7 = worker and router.
- CUSTOSZ_RUNTIME_V1 = material execution control.
- SYMPHYLAX R1 = coordination/supervision.
- Family 9 = metacognitive/evolution review.
- GitHub = transport, registry, evidence and provenance.
- Mission Mailbox = ingress + native-envelope compiler + routing bridge.

No role is silently inherited or reassigned.

## Input

missions/inbox/<mission-name>/MISSION_ORIGINAL.md

The original mission is immutable for a processing attempt. SHA-256 is its identity anchor.

The compiler does not summarize the source as authority. The native envelope carries the exact source bytes encoded as base64 and verifies reconstruction hash equality.

## State machine

DECLARED -> RECEIVED -> VALIDATED -> COMPILED
-> SEMANTICALLY_EQUIVALENT_BY_BYTE_PRESERVATION
-> ROUTED -> RUNTIME_COMPATIBLE -> EXECUTOR_BOUND
-> AUTHORIZED -> RUNNING -> VALIDATING
-> ROLLBACK_VERIFIED -> EVIDENCED -> COMPLETED

Failure branches:
- malformed input -> REJECTED
- unresolved compatibility/executor/evidence -> HOLD
- operational fault -> FAILED
- explicit cancellation -> CANCELLED

WORKFLOW_TECHNICAL_STATUS != MISSION_TERMINAL_STATUS

## Evidence products

RECEIPT.json
INGRESS_VALIDATION.json
MISSION_NATIVE.json
SEMANTIC_MAPPING.json
MISSION_STATE.json
ROUTING_DECISION.json
RUNTIME_COMPATIBILITY.json
README_ERROR.md
README_FINAL.md
CANDIDATE_GAPS.json
CAPABILITY_SUGGESTIONS.md

Persistent outputs are published under missions/registry/<MAIL_ID>/.

The registry is evidence, not canonical architecture.

## Runtime adapter boundary

The mailbox never invents a material executor.

Future material adapters are registered in mission-mailbox/runtime-adapters/registry.json. Each adapter must be explicitly named, SHA-256 pinned, capability-matched, Runtime-gated, path-constrained, auditable and reversible where mutation occurs.

No compatible adapter or no bound executor => HOLD.

## Family 9 channel

SUGGESTION != CAPABILITY
SUGGESTION != AUTHORIZATION
SUGGESTION != IMPLEMENTATION
SUGGESTION != CERTIFICATION

Only suggestions with evidence of non-duplication may be promoted to CAPABILITY_SUGGESTIONS.md. Otherwise the mailbox records a candidate gap only.

## Error contract

README_ERROR.md reports:
- expected state;
- observed state;
- root cause or UNKNOWN;
- evidence;
- affected gate;
- exact remediation;
- preconditions;
- forbidden side effects;
- binary verification test;
- rollback and rollback verification;
- next route/action;
- resolved boolean.

Absence of evidence never becomes PASS.

NO_SILENT_OPERATIONS = TRUE
FAIL_CLOSED = TRUE
TRACEABILITY_REQUIRED = TRUE
PROVENANCE_REQUIRED = TRUE
AUDITABILITY_REQUIRED = TRUE
ROLLBACK_REQUIRED_WHERE_MUTATION_OCCURS = TRUE
