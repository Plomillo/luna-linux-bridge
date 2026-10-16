{-# OPTIONS --safe --without-K #-}
module EquivalenceTransportProofs where

open import Agda.Builtin.Bool using (true; false)
open import Agda.Builtin.Equality using (_≡_; refl)
open import FalseElimination using (false-not-true; void-elim)
open import EquivalenceTransport
open EquivalenceClaim

equivalence-source-necessary :
  (e : EquivalenceClaim) ->
  equivalenceAdmissible e ≡ true ->
  sourceIdentityBound e ≡ true
equivalence-source-necessary e pass with sourceIdentityBound e
... | false = void-elim (false-not-true pass)
... | true = refl

equivalence-target-necessary :
  (e : EquivalenceClaim) ->
  equivalenceAdmissible e ≡ true ->
  targetIdentityBound e ≡ true
equivalence-target-necessary e pass with sourceIdentityBound e | targetIdentityBound e
... | false | _ = void-elim (false-not-true pass)
... | true | false = void-elim (false-not-true pass)
... | true | true = refl

equivalence-proof-necessary :
  (e : EquivalenceClaim) ->
  equivalenceAdmissible e ≡ true ->
  proofIndependentlyVerified e ≡ true
equivalence-proof-necessary e pass
  with sourceIdentityBound e | targetIdentityBound e | proofIndependentlyVerified e
... | false | _ | _ = void-elim (false-not-true pass)
... | true | false | _ = void-elim (false-not-true pass)
... | true | true | false = void-elim (false-not-true pass)
... | true | true | true = refl

equivalence-scope-necessary :
  (e : EquivalenceClaim) ->
  equivalenceAdmissible e ≡ true ->
  scopeEnumerated e ≡ true
equivalence-scope-necessary e pass
  with sourceIdentityBound e | targetIdentityBound e
     | proofIndependentlyVerified e | scopeEnumerated e
... | false | _ | _ | _ = void-elim (false-not-true pass)
... | true | false | _ | _ = void-elim (false-not-true pass)
... | true | true | false | _ = void-elim (false-not-true pass)
... | true | true | true | false = void-elim (false-not-true pass)
... | true | true | true | true = refl
