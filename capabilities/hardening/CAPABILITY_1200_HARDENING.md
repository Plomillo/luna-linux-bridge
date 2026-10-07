# CAPABILITY 1200 HARDENING CANDIDATE

STATUS = CANDIDATE_ONLY
AUTHORITY = Louksna.md
ASSURANCE = PUAC2.md
OPERATIONAL_GOVERNOR = CUSTOSZ_V7
CANONICAL_MUTATION = FALSE
CERTIFICATION_INHERITANCE = FALSE
AUTO_ACTIVATION = FALSE

## Purpose
Preserve the existing capability identities and functions while increasing resolution, testability, traceability, governance, interoperability, diagnosability, reversibility and maintainability.

## Binding rules
Every capability C MUST expose:
- capability_id
- canonical_name
- function_contract
- inputs
- outputs
- preconditions
- postconditions
- dependencies
- dependents
- provider_bindings
- evidence_requirements
- risk_profile
- resource_budget
- failure_modes
- observability_contract
- diagnosis_contract
- repair_contract
- rollback_contract
- compatibility_contract
- security_contract
- provenance_contract
- lifecycle_state
- certification_scope

## Lifecycle
DECLARED -> EVIDENCED -> VALIDATED -> INDEPENDENTLY_VALIDATED -> CERTIFIED -> ACTIVE

Forbidden shortcuts:
- DECLARED -> CERTIFIED
- EVIDENCED -> CERTIFIED
- VALIDATED -> CERTIFIED without G23
- any state -> ACTIVE without complete evidence chain and operational authorization

## PUAC2 binding
Each capability MUST map to:
- PUAC.C25 scope and claims
- PUAC.C26 evidence and argumentation
- PUAC.C27 structural independence
- PUAC.C28 security and risk
- PUAC.C29 integrity and reproducibility
- PUAC.C30 integration and non-regression
- PUAC.C31 demonstrated reversibility
- PUAC.C32 validity and reevaluation

G23 and G24 remain distinct and irreplaceable.

## Wiring invariant
NO_CAPABILITY_ISLAND = TRUE

A capability is not admissible as operationally complete unless it has:
1. at least one governed inbound relation unless it is an explicit root capability;
2. at least one governed outbound relation unless it is an explicit terminal capability;
3. declared dependency direction;
4. declared evidence flow;
5. declared failure propagation;
6. declared rollback propagation;
7. declared security boundary;
8. declared authority boundary.

## Non-duplication
Before materializing a capability, CUSTOSZ V7 MUST:
1. search existing capability identities;
2. compare semantic contracts;
3. compare providers and implementation surfaces;
4. reject duplicate implementation where composition is sufficient;
5. preserve original IDs and names.

## Change locality
A change MUST invalidate only causally affected evidence during development/maintenance, while final canonical admission remains subject to all mandatory Louksna/PUAC2 gates.

## CUSTOSZ V7 role
CUSTOSZ V7 is the principal worker for:
- discovery
- graph construction
- dependency closure
- implementation planning
- provider admission
- testing
- diagnosis
- repair
- evidence production
- rollback execution
- non-regression analysis

CUSTOSZ V7 MUST NOT self-certify and MUST NOT substitute G23 or G24.

## Required system graph edges
Every capability may use these typed edges:
- REQUIRES
- PROVIDES_TO
- VALIDATED_BY
- EVIDENCED_BY
- GOVERNED_BY
- OBSERVED_BY
- SECURED_BY
- RECOVERED_BY
- SUPERSEDES_PROVIDER_OF
- COMPATIBLE_WITH
- CONFLICTS_WITH
- BLOCKED_BY
- REPLACES_IMPLEMENTATION_OF
- LEARNS_FROM
- TEACHES
- MONITORS
- ESCALATES_TO

## Admission
A capability remains CANDIDATE/HOLD if:
- identity is unresolved;
- name was reconstructed without primary evidence;
- dependency graph is incomplete;
- evidence is stale;
- security boundary is unknown;
- rollback is unproven;
- G23 is absent where required;
- G24 is absent where required;
- operational authorization is absent.

## Preservation
B1-B134, AX0001-AX12414, Luna/Josefina/Katya/Ancapi, 14 canonical commands, E01-E15, CFE001-CFE074, G01-G24 and DOC0001-DOC0022 are outside this candidate's mutation authority.
