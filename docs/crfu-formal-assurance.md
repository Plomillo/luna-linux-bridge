# CRFU formal assurance — formal proofs and bounded runtime conformance

## 1. Purpose and preservation

This workstream closes the previously disclosed omission of actual Agda type-checking and separately adds finite, independently re-run probes against the unchanged V9 Python runtime. It is additive; it does not replace or mutate the prior CUSTOSZV9 ZIPAPP or its prior G22/G23/G24 certificate. The previously certified package SHA-256 remains `d585b351f617f4d5d134248e0c427d36ee0172b7ec32b0bdef6b7d381d394817`.

## 2. Source-level formal verification

The previous independently certified formal source commit was `99415a02c363747a2adc2404780dc6571cce8ac8`, with successful producer CI [run 38985274031](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38985274031) and trusted G22/G23/G24 [run 38985301927](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38985301927). That evidence certified its exact manifests and a 25-probe runtime conformance set. The next candidate commit must trigger a fresh producer and independent certification run; no certificate is inherited automatically.

The compiler actually found and helped correct draft errors: missing record-projection openings in the first-order modules, then ambiguity in proof patterns. The resource model's original `Bool` annotation was correct: a later compiler run showed that Agda's builtin natural-number comparison returns `Bool`. The temporary change to `Set` was reverted and this corrected inference is recorded rather than treated as a defect in the protected baseline.

Agda `2.8.0.2` and the official `agda/cubical v0.9` release are downloaded by CI only after archive SHA-256 checks pass. Every `formal/crfu/*.agda` file is checked with `--safe --without-K`; `formal/cubical/CRFUUnivalenceBridge.agda` is checked with `--cubical --safe --guardedness`. This verifies the listed files and the propositions/lemmas they contain. The Cubical bridge checks the equivalence-to-path interface and identity-equivalence path; it is not a proof that the Python implementation is globally equivalent to the specification.

## 3. Trusted bounded conformance to the unchanged runtime

The trusted G22/G23/G24 workflow is installed in `main` and its probe is checked out from the trusted workflow revision, never from the candidate branch. Before importing implementation modules, G22 hashes their exact sizes and bytes and requires them to match protected candidate baseline `b09353cbfff4efddfdec0cf853ae9658055fad2d`. G23 repeats verification of the same implementation manifest on a clean runner and runs the trusted probe in a secret-free environment. G23 attests the result, and G24 verifies that attestation before issuing a certificate tied to the exact formal and runtime manifests.

The previous, independently certified probe contained 25 checks covering planner, resource, recovery, equivalence, proof-bundle and gate-binder behavior. The new candidate probe adds ten checks, for a planned total of 35 on the next successful CI run:

- TaskContract: valid typed contract accepted; invalid source-state hash rejected.
- Coordinator: HOLD when a trusted authorization verifier is absent; DENY if an authorization result is bound to a different task; HOLD if the governed action adapter is absent; successful bounded execution with certification still `NOT_GRANTED` and canonical promotion still `NOT_AUTHORIZED`.
- Persistent SQLite mission queue: identical resubmission is idempotent; reusing a mission ID with changed task content raises a conflict; the allowed transition chain reaches RUNNING and passes the event-hash-chain verifier; a forbidden state transition is denied; a bounded wait resumes only when the exact declared signal arrives and the event chain verifies.

The new G22 implementation manifest includes the corresponding additional runtime modules `anti_paralysis.py`, `coordinator.py`, and `event_queue.py`. Their recorded bytes are required to match the protected source baseline exactly; any mismatch is a hard failure.

## 4. What the source-to-runtime mapping means

This is **bounded conformance evidence**, not a universal proof of Python-to-Agda refinement. The mapping report must state which areas have probes and which lack a direct refinement theorem:

| Formal module | Runtime evidence / boundary |
|---|---|
| `PlanSoundness.agda` | Partial bounded probes of planner guards and denial conditions; no theorem establishes the complete graph algorithm's refinement. |
| `ResourceBudgetModel.agda` | Bounded tests of `evaluate_budget` decision boundaries; not every host or integer input. |
| `RecoveryInvariant.agda` | Bounded positive and negative tests of `verify_restoration`; not production rollback. |
| `EquivalenceTransport.agda` | Bounded probes of `validate_equivalence`; not a universal equivalence theorem. |
| `ContractComposition.agda` | Partial coordinator/task pipeline probes for task validation, authorization, resource, plan and adapter gates. A complete composition-refinement theorem remains unproven. |
| `TaskAndStateModel.agda` | Bounded typed-task and persistent-queue probes for allowed/forbidden transitions, duplicate submission, deadline-bounded waits and event-chain integrity. They do not prove universal state-machine refinement. |
| `ModelImplementationCorrespondence.agda` | Proof-bundle and gate-admission behavior is probed; no theorem proves correspondence between Python source semantics and Agda semantics. |
| `MigrationCoherence.agda` | No direct migration-coherence theorem is established; recovery tests do not substitute for migration proof. |

## 5. Certification boundary

Only a successful, source-bound G22/G23/G24 chain can certify the exact manifests, formal type-checks and bounded probe results for its candidate commit. It does **not** prove universal correctness, full Python-to-Agda refinement, every Louksna axiom, every G01–G24 condition, production mTLS, production rollback, canonical promotion or operational activation.

All evidence is append-only. `Louksna.md`, `PUAC2.md`, the protected V25 baseline, the previous package artifact, its existing certificate and its earlier attestations remain unchanged. Every new source commit requires its own producer run, independent revalidation and new scope-specific certification.
