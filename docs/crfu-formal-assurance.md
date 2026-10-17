# CRFU formal assurance — bounded audit record

## Purpose

This workstream addresses the previously disclosed gap that the Agda candidates had not been type-checked. It is isolated from the prior CUSTOSZV9 ZIPAPP and its previous G22/G23/G24 evidence. The previous package SHA-256 remains `d585b351f617f4d5d134248e0c427d36ee0172b7ec32b0bdef6b7d381d394817`.

## Findings from actual compiler runs

1. The original `formal/crfu/ContractComposition.agda` failed on the first Agda 2.8.0.2 run because field projections such as `inputsValid` were not brought into scope; Agda suggested `ContractEvidence.inputsValid`. The related draft modules had analogous missing record-module openings. They have been fixed explicitly in this branch.
2. The first inspection suspected that the original resource budget type was wrong. The actual Agda compiler then disproved that suspicion: `Agda.Builtin.Nat._<_` evaluates to `Bool`. The temporary change to `Set` failed type-checking and has been reverted. The original `Bool` return type was correct. This is recorded as a corrected audit inference, not a defect in the protected parent candidate.
3. After the field-scope fixes, the actual compiler checked the plan and restoration proof files and reached the new equivalence lemmas. That run identified ambiguity in nested `with`-patterns, which have since been replaced with direct pattern matching on the evidence constructors and explicit false-equality elimination. The first successful complete compiler run is recorded at [GitHub Actions run 38984431447](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38984431447), commit `a572f63ccbb2bad660174183f9f47342b46d7a36`. The trusted G22/G23/G24 chain was merged into `main` after that run finished, so a fresh run on the next source commit is required for source-bound independent certification.
4. A Cubical Agda module is included to check the equivalence-to-path interface and identity-equivalence path against the official `agda/cubical v0.9` release. It is a narrow univalence interface, not a proof of the runtime.

## Reproducible CI

`.github/workflows/crfu-formal-assurance.yml` downloads Agda `2.8.0.2` and Cubical Agda `v0.9`, checks the release archive SHA-256 values before use, attempts to type-check every file in `formal/crfu/` using `--safe --without-K`, then type-checks the Cubical bridge using `--cubical --safe --guardedness`. It uploads logs, source files and a source-hash manifest even when the checker fails. A passing run must be followed by the separate trusted G22/G23/G24 chain before the formal source scope can be called certified.

## Certification boundary

A successful type-check means Agda verified the exact files and proofs within their declared scope. It does not by itself demonstrate that the Python runtime is a complete refinement of the Agda model, that every Louksna axiom or G01–G24 condition has a theorem, or that production rollback, host mTLS or operational behavior is validated. The Cubical bridge does not prove global implementation equivalence.

The workflow is not activation authority. No canonical `Louksna.md`, protected V25 baseline, previous CUSTOSZV9 package bytes, certificate record, earlier G22/G23/G24 attestation or release artifact is changed by this workstream. Future claims must be bound to the exact source SHA and independently validated/certified.
