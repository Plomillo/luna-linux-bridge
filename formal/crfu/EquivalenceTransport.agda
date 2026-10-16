{-# OPTIONS --safe #-}
module EquivalenceTransport where
open import Agda.Builtin.Bool using (Bool; true; false)
record EquivalenceClaim : Set where
  constructor equivalenceClaim
  field sourceIdentityBound targetIdentityBound proofIndependentlyVerified scopeEnumerated : Bool
equivalenceAdmissible : EquivalenceClaim -> Bool
equivalenceAdmissible e with sourceIdentityBound e
... | false = false
... | true with targetIdentityBound e
...   | false = false
...   | true with proofIndependentlyVerified e
...     | false = false
...     | true = scopeEnumerated e
-- Authority, authorization, signatures, certification, and binary identity are non-transportable.
