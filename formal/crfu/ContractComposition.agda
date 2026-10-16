{-# OPTIONS --safe #-}
module ContractComposition where
open import Agda.Builtin.Bool using (Bool; true; false)
record ContractEvidence : Set where
  constructor contractEvidence
  field inputsValid preconditionsPass effectsWithinScope outputsValidated : Bool
contractComposable : ContractEvidence -> Bool
contractComposable c with inputsValid c
... | false = false
... | true with preconditionsPass c
...   | false = false
...   | true with effectsWithinScope c
...     | false = false
...     | true = outputsValidated c
