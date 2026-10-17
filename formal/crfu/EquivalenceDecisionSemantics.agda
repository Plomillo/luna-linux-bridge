{-# OPTIONS --safe --without-K #-}
module EquivalenceDecisionSemantics where

open import Agda.Builtin.Bool using (Bool; true; false)
open import Agda.Builtin.Equality using (_≡_; refl)

-- Normalized semantic guards in equivalence.py. The runtime's SHA syntax,
-- object typing, proof identity and forbidden-property checks are represented
-- by predicates supplied to this decision model; this model does not claim
-- to execute or verify arbitrary Python.
record EquivalenceInput : Set where
  constructor equivalenceInput
  field
    sourceIdentityValid : Bool
    targetIdentityValid : Bool
    specificationIdentityBound : Bool
    independentProofVerified : Bool
    transportablePropertiesEnumerated : Bool
    forbiddenPropertyAbsent : Bool
open EquivalenceInput

data EquivalenceDecision : Set where
  equivalenceAdmissible equivalenceUnproven : EquivalenceDecision

equivalenceDecision : EquivalenceInput -> EquivalenceDecision
equivalenceDecision e with sourceIdentityValid e
... | false = equivalenceUnproven
... | true with targetIdentityValid e
...   | false = equivalenceUnproven
...   | true with specificationIdentityBound e
...     | false = equivalenceUnproven
...     | true with independentProofVerified e
...       | false = equivalenceUnproven
...       | true with transportablePropertiesEnumerated e
...         | false = equivalenceUnproven
...         | true with forbiddenPropertyAbsent e
...           | false = equivalenceUnproven
...           | true = equivalenceAdmissible

all-equivalence-guards-imply-admissible :
  (e : EquivalenceInput) ->
  sourceIdentityValid e ≡ true ->
  targetIdentityValid e ≡ true ->
  specificationIdentityBound e ≡ true ->
  independentProofVerified e ≡ true ->
  transportablePropertiesEnumerated e ≡ true ->
  forbiddenPropertyAbsent e ≡ true ->
  equivalenceDecision e ≡ equivalenceAdmissible
all-equivalence-guards-imply-admissible
  (equivalenceInput true true true true true true) refl refl refl refl refl refl = refl

admissibility-requires-source-identity :
  (e : EquivalenceInput) -> equivalenceDecision e ≡ equivalenceAdmissible ->
  sourceIdentityValid e ≡ true
admissibility-requires-source-identity (equivalenceInput false t s p l f) ()
admissibility-requires-source-identity (equivalenceInput true t s p l f) q = refl

admissibility-requires-target-identity :
  (e : EquivalenceInput) -> equivalenceDecision e ≡ equivalenceAdmissible ->
  targetIdentityValid e ≡ true
admissibility-requires-target-identity (equivalenceInput false t s p l f) ()
admissibility-requires-target-identity (equivalenceInput true false s p l f) ()
admissibility-requires-target-identity (equivalenceInput true true s p l f) q = refl

admissibility-requires-bound-specification :
  (e : EquivalenceInput) -> equivalenceDecision e ≡ equivalenceAdmissible ->
  specificationIdentityBound e ≡ true
admissibility-requires-bound-specification (equivalenceInput false t s p l f) ()
admissibility-requires-bound-specification (equivalenceInput true false s p l f) ()
admissibility-requires-bound-specification (equivalenceInput true true false p l f) ()
admissibility-requires-bound-specification (equivalenceInput true true true p l f) q = refl

admissibility-requires-independent-proof :
  (e : EquivalenceInput) -> equivalenceDecision e ≡ equivalenceAdmissible ->
  independentProofVerified e ≡ true
admissibility-requires-independent-proof (equivalenceInput false t s p l f) ()
admissibility-requires-independent-proof (equivalenceInput true false s p l f) ()
admissibility-requires-independent-proof (equivalenceInput true true false p l f) ()
admissibility-requires-independent-proof (equivalenceInput true true true false l f) ()
admissibility-requires-independent-proof (equivalenceInput true true true true l f) q = refl

admissibility-requires-enumerated-properties :
  (e : EquivalenceInput) -> equivalenceDecision e ≡ equivalenceAdmissible ->
  transportablePropertiesEnumerated e ≡ true
admissibility-requires-enumerated-properties (equivalenceInput false t s p l f) ()
admissibility-requires-enumerated-properties (equivalenceInput true false s p l f) ()
admissibility-requires-enumerated-properties (equivalenceInput true true false p l f) ()
admissibility-requires-enumerated-properties (equivalenceInput true true true false l f) ()
admissibility-requires-enumerated-properties (equivalenceInput true true true true false f) ()
admissibility-requires-enumerated-properties (equivalenceInput true true true true true f) q = refl

admissibility-requires-no-forbidden-property :
  (e : EquivalenceInput) -> equivalenceDecision e ≡ equivalenceAdmissible ->
  forbiddenPropertyAbsent e ≡ true
admissibility-requires-no-forbidden-property (equivalenceInput false t s p l f) ()
admissibility-requires-no-forbidden-property (equivalenceInput true false s p l f) ()
admissibility-requires-no-forbidden-property (equivalenceInput true true false p l f) ()
admissibility-requires-no-forbidden-property (equivalenceInput true true true false l f) ()
admissibility-requires-no-forbidden-property (equivalenceInput true true true true false f) ()
admissibility-requires-no-forbidden-property (equivalenceInput true true true true true false) ()
admissibility-requires-no-forbidden-property (equivalenceInput true true true true true true) q = refl
