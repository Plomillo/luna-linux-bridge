# CRFU formal assurance — bounded audit record

## Purpose and preservation

This workstream closes the previously disclosed omission of actual Agda type-checking and separately adds finite, independently re-run probes against the unchanged V9 Python runtime. It is additive and does not replace or mutate the prior CUSTOSZV9 ZIPAPP or its G22/G23/G24 certificate. The previously certified package SHA-256 remains `d585b351f617f4d5d134248e0c427d36ee0172b7ec32b0bdef6b7d381d394817`.

## Source-level formal verification already completed

At formal source commit `59a523b1269468cf6341ed08304e647183f06396`, the producer CI passed [run 38984553837](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38984553837). The trusted independent G22/G23/G24 chain passed [run 38984580172](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38984580172), issued the bounded source certificate, attested G23 at [56848419](https://github.com/Plomillo/luna-linux-bridge/attestations/56848419), and attested the G24 certificate at [56848448](https://github.com/Plomillo/luna-linux-bridge/attestations/56848448). Its formal source manifest SHA-256 was `9aa27f9b09f7777bb34db22e6166189504e663d9b1b1ae59245849e719ffe76f`, containing 13 Agda files.

The compiler actually found and helped correct draft errors: missing record projection openings in the first-order modules, then ambiguity in proof patterns. The resource model's original Bool annotation was correct: a later compiler run showed that Agda's builtin natural-number comparison returns Bool. The temporary change to Set was reverted and this corrected inference is recorded rather than treated as a defect in the protected baseline.

Agda `2.8.0.2` and the official `agda/cubical v0.9` release are downloaded by CI only after their archive SHA-256 checks pass. Every `formal/crfu/*.agda` file is checked with `--safe --without-K`; `formal/cubical/CRFUUnivalenceBridge.agda` is checked with `--cubical --safe --guardedness`. This verifies the listed files and their encoded propositions/lemmas. The Cubical bridge checks the equivalence-to-path interface and identity-equivalence path; it is not a proof that Python is equivalent to the specification.

## Additional implementation-conformance layer

The trusted G22/G23/G24 root now binds the selected Python implementation modules to the protected candidate baseline and runs a trusted probe script from the workflow's trusted revision. The probe is not loaded from the candidate branch. Before import, G22 checks source byte sizes and SHA-256 and requires each selected Python file to match the baseline commit `b09353cbfff4efddfdec0cf853ae9658055fad2d`. G23 rechecks that exact manifest on a clean runner, with a secret-free environment, and executes the finite behavior probes. G23 attests the result; G24 verifies that attestation before certifying the declared scope.

The 25 probes cover positive and negative cases for:

- planner topological order, missing dependencies, cycles, duplicate IDs, missing capabilities, forbidden effects, bounded alternatives, and the invariant that a validated plan does not itself grant execution authority;
- resource budgets for measured, unknown, RAM, disk and concurrency cases;
- recovery byte identity, state identity, dependency fingerprint, invariant checks and journal validity;
- equivalence evidence, independent verifier identity and denial of certification transport;
- proof-bundle fail-closed behavior and the global gate binder's HOLD behavior when evidence is missing.

This is **bounded conformance evidence**, not a universal proof of Python-to-Agda refinement. The mapping report deliberately preserves uncovered areas:

| Formal module | Python correspondence status |
|---|---|
| `PlanSoundness.agda` | Partial bounded probes of planner guards; resource checks are separate and no theorem establishes the complete graph algorithm's refinement. |
| `ResourceBudgetModel.agda` | Bounded tests of `evaluate_budget` decision boundaries; not every host or integer input. |
| `RecoveryInvariant.agda` | Bounded positive and negative tests of `verify_restoration`; not production rollback. |
| `EquivalenceTransport.agda` | Bounded probes of `validate_equivalence`; not a universal equivalence theorem. |
| `ModelImplementationCorrespondence.agda` | Evidence-bundle and gate-admission probes only; no theorem proves correspondence between Python source semantics and Agda semantics. |
| `ContractComposition.agda` | No exact one-to-one runtime composition theorem is established by this probe. |
| `MigrationCoherence.agda` | Recovery tests do not establish a migration-coherence proof. |
| `TaskAndStateModel.agda` | No direct refinement theorem to the persistent SQLite mission queue is established by this probe. |

## Certification boundary

A successful G22/G23/G24 run certifies only its exact source and implementation manifests, the listed formal type-checks, and the finite probe observations declared in the certificate. It does **not** prove universal correctness, full implementation refinement, all Louksna axioms, all G01–G24 conditions, production mTLS, production rollback, canonical promotion or operational activation.

All new evidence is append-only. `Louksna.md`, `PUAC2.md`, the protected V25 baseline, the previous package artifact, its existing certificate, and earlier attestations remain unchanged. A new source commit must receive its own successful CI and trusted certification; certification is never inherited automatically.
