# CRFU formal assurance — fixed V9 baseline and bounded runtime conformance

## 1. Exact scope and no-regression rule

This branch applies the compiler-checked formal CRFU model to the separately certified clean CUSTOSZV9 runtime baseline. All claims in the resulting certificate must be bound to the exact formal source commit, formal-source manifest, implementation-file manifest, package certificate, and the eight core Agda source hashes recorded in the package manifest. G22 verifies those eight source hashes and byte sizes against the sources type-checked by Agda, and verifies that no Agda source file is embedded in the operational ZIPAPP. This branch is additive and does not modify the prior CUSTOSZV9 packages, certificates or attestations, `Louksna.md`, `PUAC2.md`, or canonical authority.

**Fixed clean runtime baseline:** `58364568a66ae79de00bdea3756a4c1b03378b1d`.

**Separately certified clean package:** commit `58364568a66ae79de00bdea3756a4c1b03378b1d`, package SHA-256 `8bb088c8680331b11e8e8acc1071149c0ff37778bd84c0f27b10f91d616a5c51`, size 233,264 bytes. Its independent G22/G23/G24 decision is `CERTIFIED_FOR_DECLARED_STANDALONE_SOFTWARE_SCOPE`; its certificate JSON SHA-256 is `6dafd85769d9a37e92e399a6cca3df307c99bd616472db5bdd76da35e79ba0a3`, with Sigstore attestation at https://github.com/Plomillo/luna-linux-bridge/attestations/56856836. The successful package-certifying workflow run is [38988297744](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38988297744), with the evidence bundle at https://github.com/Plomillo/luna-linux-bridge/actions/runs/38988297744/artifacts/12084121666.

The clean package records hashes and sizes for the eight core Agda modules in `custoszv9/data/build_manifest.json`, but does not carry their `.agda` source text. The trusted formal root now verifies those eight package-manifest records against the actual source files that Agda checks, and fails closed if the runtime ZIPAPP contains formal source payload.

This package certificate does not authorize canonical promotion or operational activation. The formal assurance workflow independently downloads that certificate and evidence bundle, verifies the certificate fields, hash and Sigstore attestation, then records those identities in its own G22/G23/G24 evidence. A prior package certificate is evidence of that package only; it is not propagated to the formal scope.

## 2. Formal verification

The formal modules in this branch preserve the already compiler-checked 13 Agda source files. CI uses Agda 2.8.0.2 and the official Cubical Agda v0.9 release, checks both archive SHA-256 digests before use, type-checks every `formal/crfu/*.agda` with `--safe --without-K`, and type-checks `formal/cubical/CRFUUnivalenceBridge.agda` with `--cubical --safe --guardedness`.

A fresh compiler and independent assurance run has now passed for formal candidate commit `6c86f9cde4fbe13c0f3034e03535ee804cb64c06`, based on the clean runtime commit `58364568a66ae79de00bdea3756a4c1b03378b1d`: [producer CI 38988604783](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38988604783) and [trusted G22/G23/G24 run 38988627883](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38988627883) both passed. The formal-source manifest SHA-256 is `9aa27f9b09f7777bb34db22e6166189504e663d9b1b1ae59245849e719ffe76f` (13 files). G23 was attested at https://github.com/Plomillo/luna-linux-bridge/attestations/56857671; the G24 certificate JSON SHA-256 is `f7c5b2bf2b48a03698265c66968361fc17e458835cdb3b559994bd7d8c631435`, with its attestation at https://github.com/Plomillo/luna-linux-bridge/attestations/56857720. This scope binds the clean package SHA `8bb088c8680331b11e8e8acc1071149c0ff37778bd84c0f27b10f91d616a5c51` and its independently verified package certificate. The current commit changes only this documentation; the branch's CI and trusted root must and will re-run against the documentation-updated commit rather than inheriting the predecessor's result.

The corrected runtime addition to `TaskContract` exposes its validated source-state hash to the coordinator. That correction is included in the separately certified fixed-baseline package above. The earlier 35-probe attempt against the old baseline caught the missing property and failed closed; the failed run remains an audit record and is not treated as a pass.

## 3. Independently checked finite runtime conformance

The trusted G22/G23/G24 workflow checks that the selected runtime files are byte-identical to the fixed baseline commit and that their manifest hashes remain the same across G22 and G23. G23 runs a trusted probe sourced from the default-branch workflow revision in a secret-free clean runner, not from the candidate branch.

The expanded suite has 35 planned observations. It covers planner positive/negative cases, resource boundaries, restoration invariants, equivalence-scope constraints, proof-bundle HOLD, missing global gate evidence, typed TaskContract validation, coordinator authorization/resource/adapter gates, bounded successful coordinator execution without certification propagation, persistent SQLite mission idempotency and conflicts, allowed/forbidden state transitions, event hash-chain verification, and condition-specific deadline-bounded wait resumption.

**Latest completed result:** the extended suite has **35 PASS observations and zero failures** on formal candidate commit `6c86f9cde4fbe13c0f3034e03535ee804cb64c06`, and its independent G22/G23/G24 chain passed in [run 38988627883](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38988627883). G23 and G24 attestations are linked in Section 2. The documentation-only commit currently being created triggers the same producer checks and independent G22/G23/G24 chain again. Any failure or missing observation keeps the new commit's certification blocked. The previously certified 25-observation scope remains separate evidence and is not a substitute for the 35-observation result.

## 4. Correspondence boundaries

A successful finite run provides bounded conformance evidence, not universal Python-to-Agda refinement.

| Formal module | Runtime evidence / boundary |
|---|---|
| `PlanSoundness.agda` | Partial bounded probes of planner guards and denial conditions; no theorem establishes the full graph algorithm's refinement. |
| `ResourceBudgetModel.agda` | Bounded budget decision probes; not all hosts or integer inputs. |
| `RecoveryInvariant.agda` | Bounded positive/negative restoration tests; not production rollback. |
| `EquivalenceTransport.agda` | Bounded scope/evidence probes; not a universal equivalence theorem. |
| `ContractComposition.agda` | Partial coordinator/task-pipeline probes; complete contract-composition refinement remains unproven. |
| `TaskAndStateModel.agda` | Bounded TaskContract and SQLite queue probes; not a universal state-machine refinement theorem. |
| `ModelImplementationCorrespondence.agda` | Evidence-admission behavior is probed; a universal proof from Python source semantics to Agda semantics is not established. |
| `MigrationCoherence.agda` | Recovery tests do not establish a direct migration-coherence proof. |

HoTT/univalence is not used to prove global equivalence of the Python runtime. The Cubical module checks a declared equivalence-to-path interface; it does not establish a full implementation-refinement theorem. No claim of universal correctness for every Louksna axiom or G01–G24 gate is made.

## 5. Terminal certification boundaries

The valid success transition was completed for predecessor commit `6c86f9cde4fbe13c0f3034e03535ee804cb64c06` in trusted run `38988627883`: exact formal and runtime manifests matched, all 35 probes passed, G23 Sigstore attestation verified, G24 emitted the certificate and its attestation was verified. Because this document is being updated afterward, its new commit remains uncertified until a fresh run completes the same gates for that exact revision. Until then, only the predecessor's evidence can be claimed certified. Any failure keeps the new revision at HOLD or FAIL.

The package's separate certification remains true for its declared standalone scope. Canonical promotion remains `NOT_AUTHORIZED`; operational authorization remains `NOT_GRANTED`. This workflow cannot alter or widen those decisions. All records are append-only, and all previous artifacts/certificates/attestations remain unchanged.


## 6. Audit trail — first fixed-V9 formal root attempt and signer-path correction

For formal source commit `e1e6b7d7eb6cab612f57b0296826ddb6fccf0f2b`, the producer CI passed [run 38987066276](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38987066276). G22 and G23 also passed in trusted root run [38987092981](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38987092981), and the independent runtime probe produced exactly 35 observations with 35 PASS and zero failures. The implementation manifest SHA-256 was `6bb3f969724c0324bf0ae4af946c1a76ef04cdd3a2a42a5919c8860c4ad2e9d5`; the trusted probe SHA-256 was `38accf4eb13ac76b5886f84bfc458e9ca6192dfe07abbf9f6fa4aaa6f1c00fb8`. The formal-source manifest SHA-256 remained `9aa27f9b09f7777bb34db22e6166189504e663d9b1b1ae59245849e719ffe76f`.

G24 failed closed because the new workflow used the old workflow path when verifying the G23 Sigstore attestation and when verifying the G24 certificate attestation. The recorded error was `Error: verifying with issuer "sigstore.dev"`; no new formal certificate was accepted from that run. The source model and all 35 probes had passed; this was a trusted-root signer-identity configuration defect, not a type-checking or runtime-probe failure.

The correction is merged in [PR #77](https://github.com/Plomillo/luna-linux-bridge/pull/77), merge commit `eebd268c3fd7648b832814daa1b0fb6afbd3ad46`. Both verification commands name the exact fixed-V9 root, `.github/workflows/crfu-formal-v9fix-trusted-g22-g23-g24.yml`. Signature verification was retained; there is no bypass and no inherited certification. The corrected root subsequently passed on formal candidate `6c86f9cde4fbe13c0f3034e03535ee804cb64c06` in [run 38988627883](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38988627883), issuing the bounded clean-package formal certificate. This section update is documentation-only, but it changes the source commit; the same chain must pass again for the new commit before its certificate can be claimed.


---

## 7. Current fixed-V9 clean baseline — additive update after the V9 payload-exclusion merge

This section records the later candidate baseline without deleting or rewriting the historical evidence in Sections 1–6. Those sections describe the predecessor package with its own source commit, digest, certificate, and attestation. They must not be interpreted as the certificate record for the new package below.

**Current operational candidate source commit:** 2e6f2ce8446b3a2df831f0470701def0ae6f5819.

- The formal-source payload exclusion was integrated into its designated candidate branch by PR [#79](https://github.com/Plomillo/luna-linux-bridge/pull/79), squash merge commit 2e6f2ce8446b3a2df831f0470701def0ae6f5819. This is a candidate-branch merge, not promotion to canonical main.
- Fresh reproducible build/CLI/package validation: [run 38989403378](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38989403378), PASS.
- Fresh package G22/G23/G24 certification: [run 38989421614](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38989421614), all four jobs PASS.
- Current package SHA-256: a6bb5c8fde296f3e2b3739adbe581e1f0b26a31faaf959a6756da1fb84120831; size 233,264 bytes.
- Current package certificate JSON SHA-256: 73a35d6a4699ec9d0cda894a42706be2d58d3c132299351f897bf45285b85a54; its Sigstore attestation is [56859403](https://github.com/Plomillo/luna-linux-bridge/attestations/56859403).
- Current package evidence bundle: [run 38989421614 — artifact 12084073816](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38989421614/artifacts/12084073816).

The clean ZIPAPP still excludes the .agda source payload and records only the hashes/sizes of the eight core modules in its manifest. The exact .pyz digest changed when rebuilt against the post-merge source commit, so the formal source workflow and trusted fixed-V9 G22/G23/G24 root now bind to this new package identity and certificate. The trusted root update was merged through [PR #81](https://github.com/Plomillo/luna-linux-bridge/pull/81), which changes only the fixed-V9 formal certification workflow. The new fixed root binds its input to package commit 2e6f2ce8446b3a2df831f0470701def0ae6f5819, package SHA-256 a6bb5c8fde296f3e2b3739adbe581e1f0b26a31faaf959a6756da1fb84120831, the current package certificate hash above, and run 38989421614.

For any formal-source candidate based on this baseline, the producer CI must type-check every declared Agda module and the Cubical bridge, then the trusted fixed-V9 root must independently bind the exact formal manifest, runtime manifest, package certificate/attestation, and finite conformance results. All 35 independent Python conformance probes must pass. No formal certificate is inherited from a predecessor commit or from the earlier package SHA; each new source revision requires its own successful evidence chain.

The certificate's scope remains bounded. It does not prove universal Python-to-Agda refinement, complete ContractComposition/MigrationCoherence/TaskAndStateModel refinement, all canonical Louksna axioms or gates, production mTLS or rollback, canonical promotion, or operational activation. The prior package and formal certificates/attestations remain valid historical evidence for their exact subjects and are not rewritten, revoked, or widened by this update.
