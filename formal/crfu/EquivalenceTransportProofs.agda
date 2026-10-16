{-# OPTIONS --safe --without-K #-}
module EquivalenceTransportProofs where

open import Agda.Builtin.Bool using (true; false)
open import Agda.Builtin.Equality using (_≡_; refl)
open import EquivalenceTransport

equivalence-source-necessary :
  (e : EquivalenceClaim) ->
  equivalenceAdmissible e ≡ true ->
  sourceIdentityBound e ≡ true
equivalence-source-necessary e pass with sourceIdentityBound e
... | false with pass
...   | ()
... | true = refl

equivalence-target-necessary :
  (e : EquivalenceClaim) ->
  equivalenceAdmissible e ≡ true ->
  targetIdentityBound e ≡ true
equivalence-target-necessary e pass with sourceIdentityBound e | targetIdentityBound e
... | false | _ with pass
...   | ()
... | true | false with pass
...   | ()
... | true | true = refl

equivalence-proof-necessary :
  (e : EquivalenceClaim) ->
  equivalenceAdmissible e ≡ true ->
  proofIndependentlyVerified e ≡ true
equivalence-proof-necessary e pass
  with sourceIdentityBound e | targetIdentityBound e | proofIndependentlyVerified e
... | false | _ | _ with pass
...   | ()
... | true | false | _ with pass
...   | ()
... | true | true | false with pass
...   | ()
... | true | true | true = refl

equivalence-scope-necessary :
  (e : EquivalenceClaim) ->
  equivalenceAdmissible e ≡ true ->
  scopeEnumerated e ≡ true
equivalence-scope-necessary e pass
  with sourceIdentityBound e | targetIdentityBound e
     | proofIndependentlyVerified e | scopeEnumerated e
... | false | _ | _ | _ with pass
...   | ()
... | true | false | _ | _ with pass
...   | ()
... | true | true | false | _ with pass
...   | ()
... | true | true | true | false with pass
...   | ()
... | true | true | true | true = refl
