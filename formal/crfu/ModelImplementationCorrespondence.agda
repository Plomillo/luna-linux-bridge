{-# OPTIONS --safe #-}
module ModelImplementationCorrespondence where
open import Agda.Builtin.Bool using (Bool; true; false)
record CorrespondenceEvidence : Set where
  constructor correspondenceEvidence
  field modelIdentityBound implementationIdentityBound obligationsEnumerated checkerIndependentlyVerified : Bool
open CorrespondenceEvidence

correspondenceAdmissible : CorrespondenceEvidence -> Bool
correspondenceAdmissible e with modelIdentityBound e
... | false = false
... | true with implementationIdentityBound e
...   | false = false
...   | true with obligationsEnumerated e
...     | false = false
...     | true = checkerIndependentlyVerified e
