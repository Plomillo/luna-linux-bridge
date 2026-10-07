# DOCUMENT_FACTORY_V1 — governed specification

SPEC_ID=LOUKSNA_DOCUMENT_FACTORY_V1
SPEC_STATUS=IMPLEMENTED_CANDIDATE_NOT_CERTIFIED
RELEASE_AUTHORITY=Louksna.md
ASSURANCE_REFERENCE=PUAC2.md
CHANGE_DOCTRINE=EXTEND_DO_NOT_REPLACE
FAILURE_POSTURE=FAIL_CLOSED
NO_SILENT_OPERATIONS=TRUE
TRACEABILITY_REQUIRED=TRUE
PROVENANCE_REQUIRED=TRUE
AUDITABILITY_REQUIRED=TRUE
ROLLBACK_REQUIRED=TRUE
NON_REGRESSION_REQUIRED=TRUE
AUTO_CERTIFICATION=FORBIDDEN
CERTIFICATION_INHERITANCE=FORBIDDEN

## Generic task contract

The engine SHALL NOT encode subject-matter assumptions. Every task SHALL enter through:
1. preserved raw instructions;
2. a versioned profile;
3. requirement records with source provenance;
4. rubric criteria with exact points and validation class;
5. deliverable contracts;
6. writing constraints;
7. provider requirements;
8. explicit human/independent-review obligations.

A profile is INVALID if a mandatory requirement lacks provenance, rubric arithmetic differs from its declared total, or a required deliverable has no validation route.

## State machine

REQUEST -> INTAKE -> PROFILE_VALIDATED -> CHECKPOINT -> WRITE -> BUILD -> VERIFY
-> SELF_AUDIT -> FROZEN -> INDEPENDENTLY_VALIDATED -> CERTIFIED
-> AUTHORIZED -> ACTIVE

Exceptional states: HOLD, FAILED, QUARANTINED, RECOVERING.

Forbidden transitions include BUILD->CERTIFIED, SELF_AUDIT->G23_PASS,
G23_FAIL->G24_APPROVE, and CERTIFIED->ACTIVE without separate operational authorization.

## One-second operational control

A running stage SHALL emit a heartbeat every one second and SHALL possess timeout_seconds, max_attempts, checkpoint reference, command identity, input/output evidence, and exit status.

Timeout or stalled execution SHALL NOT trigger an unbounded retry loop. It SHALL enter HOLD, preserve diagnostics and identify the next authorized action. Retry requires a new causal basis or an explicitly equivalent pinned provider.

## Second-order metacognitive control

Self-audit SHALL inspect first-order validation and:
- reject unsupported PASS states;
- identify rubric criteria lacking evidence;
- separate automated checks from human judgment;
- expose UNKNOWN, CONFLICT and FAIL;
- reject claims stronger than the performed test;
- never assign G23 or G24.

## Writing contract

Writing SHALL remain source-first. The writer SHALL preserve requirement-to-section mapping, citation/source-ledger linkage, word-count inclusion/exclusion rules, requested section order, and distinctions required by the active profile. References or bibliographic metadata MUST NOT be fabricated or silently completed.

A writer provider MAY be human, ChatGPT, a governed agent or another declared provider. Provider success confers no canonical or certification authority.

## Provider boundary

Pandoc, LibreOffice, XLSX writer and FFprobe are replaceable providers. Their identities, versions, hashes and provenance belong to the toolchain lock and run evidence. Provider replacement requires compatibility, non-regression and applicable revalidation.

## Assurance boundary

Candidate code MAY build, verify and self-audit. Candidate code MUST NOT issue G23 or G24. G23 must consume the frozen candidate as read-only data under an independently controlled trust root. G24 must bind a favorable G23 decision and authenticated authority to the exact candidate digest.

Any mandatory FAIL, UNKNOWN or CONFLICT causes DENY/HOLD.
