# CRFU formal assurance — fixed V9 baseline and bounded runtime conformance

## 1. Exact scope and no-regression rule

This branch applies the compiler-checked formal CRFU model to the separately certified clean CUSTOSZV9 runtime baseline. All claims in the resulting certificate must be bound to the exact formal source commit, formal-source manifest, implementation-file manifest, package certificate, and the eight core Agda source hashes recorded in the package manifest. G22 verifies those eight source hashes and byte sizes against the sources type-checked by Agda, and verifies that no Agda source file is embedded in the operational ZIPAPP. This branch is additive and does not modify the prior CUSTOSZV9 packages, certificates or attestations, `Louksna.md`, `PUAC2.md`, or canonical authority.

**Fixed clean runtime baseline:** `58364568a66ae79de00bdea3756a4c1b03378b1d`.

**Separately certified clean package:** commit `58364568a66ae79de00bdea3756a4c1b03378b1d`, package SHA-256 `8bb088c8680331b11e8e8acc1071149c0ff37778bd84c0f27b10f91d616a5c51`, size 233,264 bytes. Its independent G22/G23/G24 decision is `CERTIFIED_FOR_DECLARED_STANDALONE_SOFTWARE_SCOPE`; its certificate JSON SHA-256 is `6dafd85769d9a37e92e399a6cca3df307c99bd616472db5bdd76da35e79ba0a3`, with Sigstore attestation at https://github.com/Plomillo/luna-linux-bridge/attestations/56856836. The successful package-certifying workflow run is [38988297744](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38988297744), with the evidence bundle at https://github.com/Plomillo/luna-linux-bridge/actions/runs/38988297744/artifacts/12084121666.

The clean package records hashes and sizes for the eight core Agda modules in `custoszv9/data/build_manifest.json`, but does not carry their `.agda` source text. The trusted formal root now verifies those eight package-manifest records against the actual source files that Agda checks, and fails closed if the runtime ZIPAPP contains formal source payload.

This package certificate does not authorize canonical promotion or operational activation. The formal assurance workflow independently downloads that certificate and evidence bundle, verifies the certificate fields, hash and Sigstore attestation, then records those identities in its own G22/G23/G24 evidence. A prior package certificate is evidence of that package only; it is not propagated to the formal scope.

## 2. Formal verification

The formal modules in this branch preserve the already compiler-checked 13 Agda source files. CI uses Agda 2.8.0.2 and the official Cubical Agda v0.9 release, checks both archive SHA-256 digests before use, type-checks every `formal/crfu/*.agda` with `--safe --without-K`, and type-checks `formal/cubical/CRFUUnivalenceBridge.agda` with `--cubical --safe --guardedness`.

The earlier independent source verification was successfully certified for commit `99415a02c363747a2adc2404780dc6571cce8ac8`, but was bound to the previous runtime package. This branch is based on the clean runtime source commit `58364568a66ae79de00bdea3756a4c1b03378b1d`; all 13 Agda files are present in that baseline commit and must receive a fresh compiler execution, G22 source binding, G23 independent verification, package-manifest/hash cross-check, and G24 certification. It does not inherit the earlier formal certificate automatically.

The corrected runtime addition to `TaskContract` exposes its validated source-state hash to the coordinator. That correction is included in the separately certified fixed-baseline package above. The earlier 35-probe attempt against the old baseline caught the missing property and failed closed; the failed run remains an audit record and is not treated as a pass.

## 3. Independently checked finite runtime conformance

The trusted G22/G23/G24 workflow checks that the selected runtime files are byte-identical to the fixed baseline commit and that their manifest hashes remain the same across G22 and G23. G23 runs a trusted probe sourced from the default-branch workflow revision in a secret-free clean runner, not from the candidate branch.

The expanded suite has 35 planned observations. It covers planner positive/negative cases, resource boundaries, restoration invariants, equivalence-scope constraints, proof-bundle HOLD, missing global gate evidence, typed TaskContract validation, coordinator authorization/resource/adapter gates, bounded successful coordinator execution without certification propagation, persistent SQLite mission idempotency and conflicts, allowed/forbidden state transitions, event hash-chain verification, and condition-specific deadline-bounded wait resumption.

**Certification status:** the 35-observation extended suite must not be called certified until its new producer run and trusted G22/G23/G24 chain complete successfully for this exact candidate. Any failing or missing observation keeps G23/G24 blocked. The previously certified 25-observation scope remains separate evidence and is not a substitute for this new run.

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

The only valid success transition for this scope is a new, fully source-bound G22/G23/G24 result with the exact formal and runtime manifests, 35 successful observations, verified G23 Sigstore attestation, G24 certificate, and verified G24 certificate attestation. Otherwise the outcome remains HOLD or FAIL and must be preserved as such.

The package's separate certification remains true for its declared standalone scope. Canonical promotion remains `NOT_AUTHORIZED`; operational authorization remains `NOT_GRANTED`. This workflow cannot alter or widen those decisions. All records are append-only, and all previous artifacts/certificates/attestations remain unchanged.


## 6. Audit trail — first fixed-V9 formal root attempt and signer-path correction

For formal source commit `e1e6b7d7eb6cab612f57b0296826ddb6fccf0f2b`, the producer CI passed [run 38987066276](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38987066276). G22 and G23 also passed in trusted root run [38987092981](https://github.com/Plomillo/luna-linux-bridge/actions/runs/38987092981), and the independent runtime probe produced exactly 35 observations with 35 PASS and zero failures. The implementation manifest SHA-256 was `6bb3f969724c0324bf0ae4af946c1a76ef04cdd3a2a42a5919c8860c4ad2e9d5`; the trusted probe SHA-256 was `38accf4eb13ac76b5886f84bfc458e9ca6192dfe07abbf9f6fa4aaa6f1c00fb8`. The formal-source manifest SHA-256 remained `9aa27f9b09f7777bb34db22e6166189504e663d9b1b1ae59245849e719ffe76f`.

G24 failed closed because the new workflow used the old workflow path when verifying the G23 Sigstore attestation and when verifying the G24 certificate attestation. The recorded error was `Error: verifying with issuer "sigstore.dev"`; no new formal certificate was accepted from that run. The source model and all 35 probes had passed; this was a trusted-root signer-identity configuration defect, not a type-checking or runtime-probe failure.

The correction is merged in [PR #77](https://github.com/Plomillo/luna-linux-bridge/pull/77), merge commit `eebd268c3fd7648b832814daa1b0fb6afbd3ad46`. Both verification commands now name the exact fixed-V9 root, `.github/workflows/crfu-formal-v9fix-trusted-g22-g23-g24.yml`. Signature verification was retained; there is no bypass and no inherited certification. A new formal-source commit and a fresh G22/G23/G24 run are required to verify that correction and issue a new certificate.
