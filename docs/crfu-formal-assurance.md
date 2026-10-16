# CRFU formal assurance — bounded audit record

## Purpose

This workstream addresses the previously disclosed gap that the Agda candidates had not been type-checked. It is isolated from the prior CUSTOSZV9 ZIPAPP and the prior G22/G23/G24 evidence. The previous package SHA-256 remains `d585b351f617f4d5d134248e0c427d36ee0172b7ec32b0bdef6b7d381d394817`.

## Findings from source inspection and the first actual compiler run

1. The original `formal/crfu/ResourceBudgetModel.agda` from parent commit `b09353cbfff4efddfdec0cf853ae9658055fad2d`, blob SHA `a290561c6182b2b693334d7676ad2bf784024c5`, annotated `ramSufficient` and `diskSufficient` as `Bool` while returning expressions using Agda's propositional natural-number relation `_< _ : Nat → Nat → Set`. The new isolated branch uses proposition-valued result types. The prior commit remains intact.
2. The first Agda 2.8.0.2 run failed immediately on `ContractComposition.agda`: record projections such as `inputsValid` were not in scope; Agda identified `ContractEvidence.inputsValid` as the qualified field. The same record-module opening issue was present in related draft modules. Explicit `open RecordName` declarations were added on this branch so the names resolve transparently.
3. The original candidates expressed guard predicates but lacked theorem declarations showing which individual conditions are necessary for a PASS value. Three supplementary modules add such implications for plan admissibility, restoration and equivalence-transfer checks. CI must type-check these proofs; they are not treated as proven before that run succeeds.
4. A Cubical Agda module uses the official `agda/cubical v0.9` interface to check the map from equivalence to type path and the identity-equivalence path. This checks a narrow univalence interface, not the global system.

## Reproducible CI

`.github/workflows/crfu-formal-assurance.yml` downloads Agda `2.8.0.2` and Cubical Agda `v0.9`, checks release archive SHA-256 digests before use, attempts to type-check every file in `formal/crfu/` with `--safe --without-K`, then checks the Cubical bridge with `--cubical --safe`. It uploads logs, all listed source files and a source-hash manifest. A successful build must be followed by the separate trusted G22/G23/G24 chain before this formal source scope can be called certified.

## Certification boundary

A successful type-check means the checker verified the exact files and proofs within their declared scope. It does not independently demonstrate that the Python runtime is a full refinement of these Agda definitions, that every Louksna axiom or G01–G24 condition has a theorem, or that production rollback, host mTLS or operational behavior is correct. The Cubical bridge does not prove global implementation equivalence by itself.

The workflow is not activation authority. No canonical `Louksna.md`, protected V25 baseline, prior CUSTOSZV9 package bytes, earlier certificate record, earlier G22/G23/G24 attestation or release artifact is edited by this workstream. Future claims must be bound to the exact source SHA and pass independent certification separately.
