# PUAC2 / G23 / G24 ASSURANCE CONTRACT

## Goal
Optimize for **FIRST-PASS CERTIFIABLE**, never for predetermined PASS.

## Pre-G23 dossier
Before G23, freeze exactly one candidate digest plus:
- specification/claim set;
- acceptance predicates;
- producer identities;
- input/output hashes;
- dependency/currentness report;
- provenance chain;
- positive/negative/boundary tests;
- rollback proof;
- non-regression report;
- security/privacy/data-rights report where applicable;
- unresolved findings.

## G23
G23 is read-only independent validation. It SHALL NOT repair the candidate or rewrite producer evidence.

Current repository-local validation can prove only `PRE_G23_READINESS` unless independence from the producer is materially established. A fresh runner alone is insufficient if the producer can also mutate the validator in the same unprotected trust domain.

## G24
G24 evaluates only the same frozen digest accepted by G23. Any digest change returns the system to validation.

```text
TECHNICAL_SUCCESS != G23
G23 != G24
G24_PASS_REQUIRED_FOR_CERTIFICATION = TRUE
```

## Fail closed
Any missing evidence is `HOLD` or `FAIL` according to the applicable contract; it is never inferred as PASS.
