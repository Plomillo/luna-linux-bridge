# CRFU formal assurance — bounded audit record

## Purpose

This workstream closes the previously disclosed gap that the Agda candidates were not type-checked. It is deliberately isolated from the prior CUSTOSZV9 ZIPAPP and its earlier G22/G23/G24 evidence. The exact package SHA-256 associated with the earlier scoped certificate remains
`d585b351f617f4d5d134248e0c427d36ee0172b7ec32b0bdef6b7d381d394817`.

## Findings from the source audit

- The original `formal/crfu/ResourceBudgetModel.agda` from parent commit `b09353cbfff4efddfdec0cf853ae9658055fad2d` has Git blob SHA `a290561c6182b2b693334d7676ad2bf784024c5`. Its functions were annotated to return `Bool`, while the imported Agda builtin natural-number relation `_< _` has propositional type `Set`. This is a concrete type mismatch. The formal-assurance branch corrects the model's result types to `Set`, preserving strict inequalities as propositions. The parent commit and original package are unchanged.
- The original plan, restoration and equivalence modules encoded admission rules, but did not include lemmas demonstrating that a PASS result implies each constituent check. New Agda modules provide those implications as type-checked lemmas, if CI passes.
- A Cubical Agda bridge is included and checked against the pinned `agda/cubical v0.9` release. It validates only the equivalence-to-path interface and identity-equivalence path, not the runtime.

## Reproducible CI

`.github/workflows/crfu-formal-assurance.yml` installs the official Agda `2.8.0.2` Linux release and Cubical Agda `v0.9`, checking their release archive SHA-256 values before use. It attempts to type-check every file in `formal/crfu/` under `--safe --without-K` and the Cubical module under `--cubical --safe`. The workflow uploads exact source files, source hashes and compiler logs as evidence. A green run is required before claiming the declared source-level formal scope passed.

## Certification boundary

A successful type-check means Agda verified the actual files and proofs within their declared scope. It does not establish all of the following without additional bridges and evidence:

- that all Python CRFU paths are a faithful refinement of these Agda definitions;
- that every Louksna invariant or every G01–G24 condition has a formal theorem;
- that runtime resource probes, system rollback, host mTLS or operational production behavior are formally or empirically validated;
- that the full CUSTOSZV9 package is globally correct or eligible for operational activation;
- that univalence has been used to prove global equivalence of the implementation to the specification.

The workflow is not an activation authority. No canonical `Louksna.md`, protected V25 baseline, previous package, existing certificate, G22/G23/G24 attestation or release artifact is modified by these files. All new claims must be bound to the source SHA and later pass independent validation/certification separately.
