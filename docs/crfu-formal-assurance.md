# CRFU formal assurance — mathematical closure addendum

## Immutable predecessor evidence

The previously certified CUSTOSZV9 packages, their source commits, package digests, certificate records, G23/G24 attestations, and historical workflow artifacts are immutable predecessor evidence. This change is additive. It does not overwrite those objects, change canonical authority, authorize activation, or propagate certification from one hash to another.

The V9 package and formal-source certifications remain scoped to their exact subject hashes. The new formal source commit must pass its own pinned compiler checks and its own independent G22/G23/G24 chain before this addendum can be considered certified.

## Mathematical work added in this candidate

- formal/cubical/CRFUUnivalenceBridge.agda states the Cubical univalence equivalence (A ≡ B) ≃ (A ≃ B), both inverse laws, the computation rule for transport along ua, and the identity-equivalence path rule.
- formal/crfu/CRFUClosureTheorems.agda adds sufficient-condition proofs complementing existing necessity proofs for plan, contract-composition, migration-coherence, recovery, and equivalence guards. It adds a versioned task decision model with separate safe-ready, hold-for-evidence, and forbidden-action denial cases, plus a task lifecycle relation with terminal-state no-outgoing-transition proofs. The previous TaskAndStateModel.agda remains byte-identical: its compiler warnings show that its false pattern shadows the Bool constructor, so the new proofs do not falsely attribute correct hold behavior to that legacy source.
- formal/crfu/ResourceBudgetRuntimeSemantics.agda defines the inclusive RAM/disk boundary semantics present in custoszv9/crfu/resources.py, including natural-number subtraction truncated at zero.
- formal/crfu/ResourceBudgetRuntimeSemanticsProofs.agda proves concrete boundary facts and explicitly demonstrates the equality-boundary disagreement with the historical strict ResourceBudgetModel.agda. No prior source file is silently rewritten.

## Automated validation and evidence

The existing GitHub Actions formal-assurance producer type-checks every first-order formal/crfu/*.agda file with verified Agda 2.8.0.2 and the Cubical bridge with verified Cubical Agda v0.9. Its independent trust-root workflow performs G22 source/package binding, G23 clean-runner validation and attestation, and G24 certificate/attestation checks. This candidate is not certified merely because a producer workflow succeeds; the exact candidate must complete the independent trusted chain.

Acceptance conditions: all source modules type-check; univalence and resource boundary proofs type-check; predecessor V8/V9 evidence remains unchanged; G22 binds this exact candidate; G23 independently validates and attests its result; and G24 verifies that attestation before issuing a scope-limited certificate.

## Explicit scope boundary

These proofs establish the stated Agda/Cubical propositions. The resource boundary proof captures the arithmetic contract present in the Python function, while existing Python probes remain bounded behavioral evidence. The new task decision model corrects the formal specification in an additive module; it does not claim that the legacy model or runtime implementation has a universal refinement proof. This addendum does not claim a universal theorem translating arbitrary Python source execution into Agda semantics. That stronger claim requires an independently verified source-to-model relation or verified implementation and must not be inferred from type-checking or test success alone. Global canonical G01-G24 certification, exact V25 baseline byte-comparison, canonical promotion, and operational activation remain outside this formal-only certificate unless their separate required evidence is supplied and validated.
