# WIRING PLAN — 1–1200

This plan does not add or rename capabilities. It binds existing identities into one governed graph.

## Layer A — Identity and authority
All capabilities bind to Louksna.md authority, preserve canonical identity, and are subordinate to G01-G24.

## Layer B — Evidence and assurance
Every capability binds its claims/evidence to PUAC.C25-C32 and to G23/G24 where admission requires them.

## Layer C — Runtime
CUSTOSZ V7 discovers, plans, invokes providers, observes state, diagnoses failures, produces evidence and requests gates. CUSTOSZ V7 never self-certifies.

## Layer D — Shared fabrics
Cross-domain capabilities are shared by reference, not copied:
- provenance
- traceability
- audit
- uncertainty reduction
- maintenance
- security
- recovery
- compatibility
- pedagogy
- knowledge memory

## Layer E — Domain graph
Domain capabilities declare REQUIRES/PROVIDES_TO/SECURED_BY/RECOVERED_BY/VALIDATED_BY edges. Cycles require explicit justification and termination semantics.

## Layer F — Provider independence
Providers are replaceable implementations. Capability identity survives provider replacement. A provider swap creates fresh evidence and impact analysis.

## Layer G — Change propagation
Changes trigger reverse-dependency analysis, affected-test selection, evidence invalidation and scoped revalidation. Final canonical admission remains governed by mandatory gates.

## Layer H — Failure propagation
Each capability declares:
- local failure
- propagated failure
- containment boundary
- degradation mode
- fail-closed conditions
- recovery owner
- rollback target

## Layer I — Security continuity
Security may quarantine or block an implementation but MUST preserve a governed path to recover legitimate capability through sanitization, trusted replacement or safe reimplementation when demonstrable.

## Layer J — Long-term survival
Knowledge is stored as contracts, graphs, tests, evidence, runbooks, histories and provider-independent interfaces so model/provider replacement does not destroy operational intelligence.
